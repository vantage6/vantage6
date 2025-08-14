import datetime
import logging
from http import HTTPStatus

from flask import g, request, url_for
from marshmallow import ValidationError
from sqlalchemy import select

from vantage6.common.encryption import DummyCryptor
from vantage6.common.enum import (
    AlgorithmStepType,
    RunStatus,
    TaskDatabaseType,
    TaskStatus,
)
from vantage6.common.globals import STRING_ENCODING, NodeConfigKey, NodePolicy

from vantage6.backend.common.resource.error_handling import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    handle_exceptions,
)

from vantage6.server import db
from vantage6.server.algo_store_communication import request_algo_store
from vantage6.server.dataclass import CreateTaskDB
from vantage6.server.permission import (
    Operation as P,
    RuleCollection,
)
from vantage6.server.resource import ServicesResources
from vantage6.server.resource.common.input_schema import TaskInputSchema
from vantage6.server.resource.common.output_schema import TaskSchema

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)

task_input_schema = TaskInputSchema()
task_schema = TaskSchema()


class TaskPostBase(ServicesResources):
    """
    Base class for task posting.

    This is inherited by the different task posting endpoints, such as /task, /dataframe
    and /preprocessing.
    """

    # TODO this function should be refactored to make it more readable
    @handle_exceptions
    def post_task(
        self,
        data: dict,
        rules: RuleCollection,
        action: AlgorithmStepType | None = None,
        should_be_compute: bool = False,
    ) -> tuple[dict, HTTPStatus]:
        """
        Create new task and algorithm runs. Send the task to the nodes.

        Parameters
        ----------
        data : dict
            Task data
        rules : RuleCollection
            Rule collection instance
        config : dict
            Configuration dictionary
        action : AlgorithmStepType | None
            Action to performed by the task. If not provided, the action will be
            inferred from the algorithm.
        should_be_compute : bool
            Whether the task should be a compute task. Default is False.

        Returns
        -------
        tuple[dict, HTTPStatus]
            Tuple containing the response and the HTTP status code.
        """
        self._validate_request_body(data)

        session = self._validate_session(data["session_id"])

        collaboration, study = self._validate_collaboration_and_study(data)

        organizations_json_list = data.get("organizations")
        org_ids = [org.get("id") for org in organizations_json_list]

        self._validate_organizations_in_collaboration(org_ids, collaboration, study)

        nodes = self._validate_nodes_exist(org_ids, collaboration)

        if g.user:
            self._validate_node_allows_user_task(nodes)

        init_org = self._validate_init_org(collaboration)

        # verify permissions
        image = data.get("image", "")
        if g.user and not rules.can_for_col(P.CREATE, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED
        elif g.container and not self.__verify_container_permissions(
            g.container, image, collaboration.id
        ):
            return {"msg": "Container-token is not valid"}, HTTPStatus.UNAUTHORIZED

        image_with_hash, store, algorithm = self.get_algorithm(
            data.get("store_id"), collaboration.id, image
        )
        self._check_image_allowed_in_session(image_with_hash, session, collaboration)

        # check the action of the task
        action = self.__check_action(data, action, algorithm, should_be_compute)

        dependent_tasks = self._get_dependent_tasks(
            data, action, session, org_ids, collaboration
        )

        self._check_arguments_encryption(organizations_json_list, collaboration)

        # everything ok, create task record, task database records and run records
        task = self._create_task(
            data,
            collaboration,
            study,
            image_with_hash,
            store,
            init_org,
            session,
            dependent_tasks,
        )
        if g.user:
            self._on_user_created_task(task)
        elif g.container:
            self._on_container_created_task(task)
        self._create_task_databases(task, data.get("databases", [[]]))
        self._create_runs(task, organizations_json_list, action)

        # alerting and logging
        self._notify_nodes_of_new_task(task)
        self._new_task_logging(task)

        return task_schema.dump(task, many=False), HTTPStatus.CREATED

    def _validate_request_body(self, data: dict) -> None:
        # validate request body
        try:
            data = task_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

    def _validate_session(self, session_id: int) -> db.Session:
        session = db.Session.get(session_id)
        if not session:
            raise NotFoundError(f"Session id={session_id} not found!")
        return session

    def _validate_collaboration_and_study(
        self, data: dict
    ) -> tuple[db.Collaboration, db.Study | None]:
        # A task can be created for a collaboration or a study. If it is for a study,
        # a study_id is always given, and a collaboration_id is optional. If it is for
        # a collaboration, a collaboration_id is always given, and a study_id is
        # never set. The following logic checks if the given study_id and
        # collaboration_id are valid and when both are provided, checks if they match.
        collaboration_id = data.get("collaboration_id")
        study_id = data.get("study_id")

        if not collaboration_id and not study_id:
            raise BadRequestError(
                "Either a collaboration_id or a study_id should be provided!"
            )

        study = None
        if collaboration_id:
            collaboration = db.Collaboration.get(collaboration_id)
            if not collaboration:
                raise NotFoundError(f"Collaboration id={collaboration_id} not found!")
        if study_id:
            study = db.Study.get(study_id)
            if not study:
                raise NotFoundError(f"Study id={study_id} not found")

            # check if collaboration and study match if both are set
            if collaboration_id and study.collaboration_id != collaboration_id:
                raise BadRequestError(
                    f"The study_id '{study.id}' does not belong to the "
                    f"collaboration_id '{collaboration_id}' that is given."
                )

            # get the collaboration object as well
            collaboration_id = study.collaboration_id
            collaboration = db.Collaboration.get(collaboration_id)
        return collaboration, study

    def _validate_organizations_in_collaboration(
        self,
        org_ids: list[int],
        collaboration: db.Collaboration,
        study: db.Study | None,
    ) -> None:
        db_ids = collaboration.get_organization_ids()

        # Check that all organization ids are within the collaboration, this
        # also ensures us that the organizations exist
        if not set(org_ids).issubset(db_ids):
            raise BadRequestError(
                "At least one of the supplied organizations in not within "
                "the collaboration."
            )

        # check that they are within the study (if that has been defined)
        if study:
            study_org_ids = [org.id for org in study.organizations]
            if not set(org_ids).issubset(study_org_ids):
                raise BadRequestError(
                    "At least one of the supplied organizations in not within "
                    "the specified study."
                )

    def _validate_nodes_exist(
        self, org_ids: list[int], collaboration: db.Collaboration
    ) -> None:
        """Check if all the organizations have a registered node"""
        nodes = g.session.scalars(
            select(db.Node)
            .filter(db.Node.organization_id.in_(org_ids))
            .filter(db.Node.collaboration_id == collaboration.id)
        ).all()
        if len(nodes) < len(org_ids):
            present_nodes = [node.organization_id for node in nodes]
            missing = [str(id) for id in org_ids if id not in present_nodes]
            raise BadRequestError(
                "Cannot create this task because there are no nodes registered"
                f" for the following organization(s): {', '.join(missing)}."
            )
        return nodes

    def _validate_node_allows_user_task(self, nodes: list[db.Node]) -> None:
        """
        Check if any of the nodes that are offline shared their configuration
        info and if this prevents this user from creating this task

        """
        for node in nodes:
            if self._node_doesnt_allow_user_task(node.config):
                raise BadRequestError(
                    "Cannot create this task because one of the nodes that"
                    " you are trying to send this task to does not allow "
                    "you to create tasks."
                )

    def _validate_init_org(self, collaboration: db.Collaboration) -> db.Organization:
        """
        Validate the initiating organization of the task.
        """
        if g.user:
            init_org = g.user.organization
        else:  # g.container:
            init_org = db.Node.get(g.container["node_id"]).organization

            # check if the initiating organization is part of the collaboration
        if init_org not in collaboration.organizations:
            raise ForbiddenError(
                "You can only create tasks for collaborations you are participating in!"
            )
        return init_org

    def _check_image_allowed_in_session(
        self, image_with_hash: str, session: db.Session, collaboration: db.Collaboration
    ) -> None:
        """Check if the image can be run within this session"""
        if (
            collaboration.session_restrict_to_same_image
            and session.image != image_with_hash
        ):
            raise BadRequestError(
                f"The session is restricted to the single image '{session.image}'. "
                f"You cannot create a task with image '{image_with_hash}'."
            )

    def _get_dependent_tasks(
        self,
        data: dict,
        action: AlgorithmStepType,
        session: db.Session,
        org_ids: list[int],
        collaboration: db.Collaboration,
    ) -> list[db.Task]:
        """
        Get the dependent tasks for the task.
        """
        # A task can be dependent on one or more other task(s). There are three cases:
        #
        # 1. When a dataframe modification task is created (data extraction or
        #    preprocessing) the next modification task should be dependent on the
        #    previous modification task. This is to prevent that the dataframe is
        #    modified by two tasks at the same time.
        # 2. When a dataframe modification task is created, the task should be dependent
        #    on the compute task(s) that are currently computing the dataframe. This is
        #    to prevent that the dataframe is modified during the computation.
        # 3. When a compute task is created, the task should be dependent on the
        #    modification task(s) that are currently modifying the dataframe. This is
        #    to prevent that the dataframe is modified during the computation.
        #
        # Thus when a modification task is running, all new compute tasks and all new
        # modification tasks will be depending on it. When a compute task is running,
        # all new modification tasks will depend on it. The `depends_on_ids` parameter
        # is set by the session endpoints.
        dependent_tasks = []
        databases = data.get("databases", [[]])
        for database in [
            CreateTaskDB.from_dict(db_) for sublist in databases for db_ in sublist
        ]:
            # add last modification task to dependent tasks
            if database.type == TaskDatabaseType.DATAFRAME:
                df = db.Dataframe.get(database.dataframe_id)
                if not df:
                    raise NotFoundError(f"Dataframe '{database.label}' not found!")

                if not df.ready:
                    dependent_tasks.append(df.last_session_task)

            # If dataframe extraction is not ready for each org, don't create task
            if action != AlgorithmStepType.DATA_EXTRACTION:
                self._check_data_extract_ready_for_requested_orgs(df, org_ids)
            else:
                self.__check_database_label_exists(
                    database.label, org_ids, collaboration.id
                )

        # These `depends_on_ids` are the task ids supplied by the session endpoints.
        # However they can also be user defined, although this has no use case yet.
        dependent_task_ids = data.get("depends_on_ids", [])
        for dependent_task_id in dependent_task_ids:
            dependent_task = db.Task.get(dependent_task_id)

            if not dependent_task:
                raise NotFoundError(f"Task with id={dependent_task_id} not found!")

            if dependent_task.session_id != session.id:
                raise BadRequestError(
                    "The task you are trying to depend on is not part of the "
                    "same session."
                )

            dependent_tasks.append(dependent_task)

        # Filter that we did not end up with duplicates because of various conditions
        return list(set(dependent_tasks))

    def _create_task(
        self,
        data: dict,
        collaboration: db.Collaboration,
        study: db.Study | None,
        image_with_hash: str,
        store: db.AlgorithmStore,
        init_org: db.Organization,
        session: db.Session,
        dependent_tasks: list[db.Task],
    ) -> db.Task:
        """
        Create a task record and related records.
        """
        task = db.Task(
            collaboration=collaboration,
            study=study,
            name=data.get("name", ""),
            description=data.get("description", ""),
            image=image_with_hash,
            method=data["method"],
            init_org=init_org,
            algorithm_store=store,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            session=session,
            depends_on=dependent_tasks,
            dataframe_id=data.get("dataframe_id"),
        )
        task.save()
        return task

    def _on_user_created_task(self, task: db.Task) -> None:
        """
        Create a job_id and save the task to the database.
        """
        task.job_id = task.next_job_id()
        task.init_user_id = g.user.id
        log.debug("New job_id %s", task.job_id)
        task.save()

    def _on_container_created_task(self, task: db.Task) -> None:
        parent = db.Task.get(g.container["task_id"])
        task.parent_id = parent.id
        task.job_id = parent.job_id
        task.init_user_id = parent.init_user_id
        task.save()
        log.debug("New subtask from parent_id=%s", task.parent_id)

    def _create_task_databases(
        self, task: db.Task, databases: list[list[dict]]
    ) -> None:
        """
        Create the task databases.
        """
        # save the databases that the task uses
        for idx, database_group in enumerate(databases):
            # TODO task.id is only set here because in between creating the
            # task and using the ID here, there are other database operations
            # that silently update the task.id (i.e. next_job_id() and
            # db.Task.get()). Task.id should be updated explicitly instead.
            for database in [CreateTaskDB.from_dict(db_) for db_ in database_group]:
                task_db = db.TaskDatabase(
                    task_id=task.id,
                    label=database.label,
                    type_=database.type.value,
                    dataframe_id=database.dataframe_id,
                    position=idx,
                )
                task_db.save()

    def _create_runs(
        self,
        task: db.Task,
        organizations_json_list: list[dict],
        action: AlgorithmStepType,
    ) -> None:
        """
        Create the runs.
        """
        log.debug("Assigning task to %s nodes.", len(organizations_json_list))
        for org in organizations_json_list:
            organization = db.Organization.get(org["id"])
            log.debug("Assigning task to '%s'.", organization.name)
            arguments = org.get("arguments")
            # Create run
            run = db.Run(
                task=task,
                organization=organization,
                arguments=arguments,
                status=RunStatus.PENDING.value,
                action=action.value,
            )
            run.save()

    def _notify_nodes_of_new_task(self, task: db.Task) -> None:
        self.socketio.emit(
            "new_task_update",
            {"id": task.id, "parent_id": task.parent_id},
            namespace="/tasks",
            room=f"collaboration_{task.collaboration_id}",
        )

    def _new_task_logging(self, task: db.Task) -> None:
        log.info("New task for collaboration '%s'", task.collaboration.name)
        if g.user:
            log.debug(" created by: '%s'", g.user.username)
        else:
            log.debug(
                " created by container on node_id=%s for (parent) task_id=%s",
                g.container["node_id"],
                g.container["task_id"],
            )

        log.debug(" url: '%s'", url_for("task_with_id", id=task.id))
        log.debug(" name: '%s'", task.name)
        log.debug(" image: '%s'", task.image)
        log.debug(" session ID: '%s'", task.session_id)

    @staticmethod
    def __verify_container_permissions(container, image, collaboration_id):
        """Validates that the container is allowed to create the task."""

        # check that node id is indeed part of the collaboration
        if not container["collaboration_id"] == collaboration_id:
            log.warning(
                "Container attempts to create a task for collaboration_id=%s in "
                "collaboration_id=%s!",
                container["collaboration_id"],
                collaboration_id,
            )
            return False

        # check that parent task is not completed yet
        if TaskStatus.has_finished(db.Task.get(container["task_id"]).status):
            log.warning(
                "Container from node=%s attempts to start sub-task for a completed "
                "task=%s",
                container["node_id"],
                container["task_id"],
            )
            return False

        return True

    @staticmethod
    def __check_database_label_exists(
        label: str, org_ids: list[int], collaboration_id: int
    ) -> bool:
        """
        Check if the database label exists, if node configuration is shared for that.

        Parameters
        ----------
        label : str
            Label of the database.
        org_ids : list[int]
            List of organization IDs that task is requested for.
        collaboration_id : int
            ID of the collaboration.

        Raises
        ------
        BadRequestError
            If the database label does not exist for any of the organizations.
        """
        for org_id in org_ids:
            node = db.Node.get_by_org_and_collab(org_id, collaboration_id)
            if not node.config:
                continue

            db_labels_available = [
                config.value
                for config in node.config
                if config.key == NodeConfigKey.DATABASE_LABELS
            ]
            if label not in db_labels_available:
                raise BadRequestError(
                    f"The database label '{label}' does not exist for organization "
                    f"{org_id}."
                )

    @staticmethod
    def _check_data_extract_ready_for_requested_orgs(
        dataframe: db.Dataframe, org_ids: list[int]
    ) -> bool:
        """
        Check if at least one dataframe extraction run succeeded.

        Parameters
        ----------
        dataframe : db.Dataframe
            Dataframe to check.
        org_ids : list[int]
            List of organization IDs that task is requested for.

        Returns
        -------
        bool
            True if the dataframe extraction succeeded, False otherwise.
        """
        org_ids_succeeded = dataframe.organizations_ready()
        org_ids_not_succeeded = set(org_ids) - set(org_ids_succeeded)
        if org_ids_not_succeeded:
            raise BadRequestError(
                "The dataframe you selected is not present for the following "
                f"organizations: {', '.join(str(i) for i in org_ids_not_succeeded)}. "
                "Cannot create a task if the dataframe is not present for all requested"
                " organizations."
            )

    @staticmethod
    def _node_doesnt_allow_user_task(node_configs: list[db.NodeConfig]) -> bool:
        """
        Checks if the node allows user to create task.

        Parameters
        ----------
        node_configs : list[db.NodeConfig]
            List of node configurations.

        Returns
        -------
        bool
            True if the node doesn't allow the user to create task.
        """
        has_limitations = False
        for config_option in node_configs:
            if config_option.key == NodePolicy.ALLOWED_USERS:
                has_limitations = True
                # TODO expand when we allow also usernames, like orgs below
                if g.user.id == int(config_option.value):
                    return False
            elif config_option.key == "allowed_orgs":
                has_limitations = True
                if config_option.value.isdigit():
                    if g.user.organization_id == int(config_option.value):
                        return False
                else:
                    org = db.Organization.get_by_name(config_option.value)
                    if org and g.user.organization_id == org.id:
                        return False
        return has_limitations

    @staticmethod
    def _check_arguments_encryption(
        organizations_json_list: list[dict], collaboration: db.Collaboration
    ) -> None:
        """
        Check if the function arguments encryption status matches the expected status
        for the collaboration. Also, check that if the function arguments are not
        encrypted, they can be read as a string.

        Parameters
        ----------
        organizations_json_list : list[dict]
            List of organizations which contains the encrypted function arguments per
            organization.
        collaboration : db.Collaboration
            Collaboration object.

        Raises
        ------
        BadRequestError
            If the function arguments are not encrypted and the collaboration is set to
            use encryption.
        """
        # check that the input for function arguments is valid. If the collaboration is
        # encrypted, it should not be possible to read the arguments, and we should not
        # save it to the database as it may be sensitive information. Vice versa, if
        # the collaboration is not encrypted, we should not allow the user to
        # send encrypted function arguments.
        dummy_cryptor = DummyCryptor()
        for org in organizations_json_list:
            arguments = org.get("arguments")
            if arguments is None:
                continue
            decrypted_arguments = dummy_cryptor.decrypt_str_to_bytes(arguments)
            are_arguments_readable = False
            try:
                decrypted_arguments.decode(STRING_ENCODING)
                are_arguments_readable = True
            except UnicodeDecodeError:
                pass

            if collaboration.encrypted and are_arguments_readable:
                raise BadRequestError(
                    "Your collaboration requires encryption, but function arguments"
                    " are not encrypted! Please encrypt your function arguments "
                    "before sending them."
                )
            elif not collaboration.encrypted and not are_arguments_readable:
                raise BadRequestError(
                    "Your task's function arguments cannot be parsed. Your function "
                    "arguments should be a base64 encoded JSON string. Note that if "
                    "you are using the user interface or Python client, this should "
                    "be done for you. Also, make sure not to encrypt your function "
                    "arguments, as your collaboration is set to not use encryption."
                    "as your collaboration is set to not use encryption."
                )

    @staticmethod
    def __check_action(
        request_data: dict,
        action: AlgorithmStepType | None,
        algorithm: dict | None,
        should_be_compute: bool,
    ) -> AlgorithmStepType:
        """
        Check if the action of the task matches the action in the algorithm store. If
        no action is provided, use the action from the algorithm store.

        Parameters
        ----------
        request_data : dict
            Request data.
        action : AlgorithmStepType | None
            Action to be performed.
        algorithm : dict | None
            Algorithm object from algorithm store.
        should_be_compute : bool
            Whether the task should be a compute task.

        Raises
        ------
        Exception
            If the action is not valid or does not match the action type in the
            algorithm store.
        """
        method = request_data["method"]
        if not action and request_data.get("action"):
            action = AlgorithmStepType(request_data.get("action"))
        store_action = None
        if algorithm:
            algo_func = next(
                (f for f in algorithm["functions"] if f["name"] == method), None
            )
            store_action = (
                AlgorithmStepType(algo_func["step_type"]) if algo_func else None
            )

        if action and store_action and action != store_action:
            raise BadRequestError(
                f"Action {action} does not match the action type in the "
                f"algorithm store: {store_action}"
            )
        elif not action and not store_action:
            raise BadRequestError(
                "No action type provided. Please provide an action that is one of: "
                f"{AlgorithmStepType.list()}"
            )

        elif not action:
            action = store_action

        if should_be_compute and not AlgorithmStepType.is_compute(action):
            msg = f"A {action.value} task cannot be created in this endpoint."
            if action == AlgorithmStepType.DATA_EXTRACTION:
                msg += (
                    " Please use the dataframe endpoint to create a dataframe "
                    "extraction task."
                )
            elif action == AlgorithmStepType.PREPROCESSING:
                msg += (
                    " Please use the dataframe endpoint to create a preprocessing task."
                )
            raise BadRequestError(msg)

        return action

    def get_algorithm(
        self, store_id: int | None, collaboration_id: int, image: str
    ) -> tuple[str, db.AlgorithmStore, dict]:
        """
        Get the algorithm from the store or the image.
        """
        # get the algorithm store
        algorithm = None
        if g.user:
            store = None
            if store_id:
                store = db.AlgorithmStore.get(store_id)
                if not store:
                    raise BadRequestError(f"Algorithm store id={store_id} not found!")
                # check if the store is part of the collaboration
                if (
                    not store.is_for_all_collaborations()
                    and store.collaboration_id != collaboration_id
                ):
                    raise ForbiddenError(
                        "The algorithm store is not part of the collaboration "
                        "to which the task is posted."
                    )
                # get the algorithm from the algorithm store
                try:
                    algorithm = self._get_algorithm_from_store(store=store, image=image)
                    image = algorithm["image"]
                    digest = algorithm["digest"]
                except Exception as e:
                    log.exception("Error while getting image from store: %s", e)
                    raise BadRequestError(str(e)) from e

                if digest:
                    image_with_hash = f"{image}@{digest}"
                else:
                    # hash lookup in store was unsuccessful, use image without hash, but
                    # also set store to None as it was not successfully looked up
                    image_with_hash = image
                    store = None
            else:
                # no need to determine hash if we don't look it up in a store
                image_with_hash = image
        else:  # ( we are dealing with g.container)
            parent = db.Task.get(g.container["task_id"])
            store = parent.algorithm_store
            image_with_hash = parent.image

        return image_with_hash, store, algorithm

    @staticmethod
    def _get_algorithm_from_store(
        store: db.AlgorithmStore,
        image: str,
    ) -> dict:
        """
        Determine the image and hash from the algorithm store.

        Parameters
        ----------
        store : db.AlgorithmStore
            Algorithm store.
        image : str
            URL of the docker image to be used.

        Returns
        -------
        dict
            Algorithm object from algorithm store.

        Raises
        ------
        Exception
            If the algorithm cannot be retrieved from the store.
        """
        # get the algorithm from the store
        response, status_code = request_algo_store(
            algo_store_url=f"{store.url}{store.api_path}",
            endpoint="algorithm",
            method="GET",
            params={"image": image},
            headers={"Authorization": request.headers["Authorization"]},
        )
        if status_code != HTTPStatus.OK:
            raise Exception(
                f"Could not retrieve algorithm from store! {response.get('msg')}"
            )
        try:
            algorithm = response.json()["data"][0]
        except Exception as e:
            raise Exception("Algorithm not found in store!") from e

        return algorithm
