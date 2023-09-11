import logging
import time
import pickle

from vantage6.server import db
from vantage6.client.encryption import DummyCryptor


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

NODE_ONLINE_CHECK_IMAGE = "harbor2.vantage6.ai/starter/utils"
TIME_WAIT_NODE_RESPONSE = 120


def run(collaboration_id: int, socketio):
    """
    Create a task to check which nodes are online for the given collaboration.
    """
    time.sleep(10)
    collab = db.Collaboration.get(collaboration_id)

    # Create a task for all nodes in the collaboration
    task = db.Task(
        collaboration_id=collaboration_id,
        name="node_online_check",
        description="Dummy task to check which nodes are online",
        image=NODE_ONLINE_CHECK_IMAGE,
        initiator=collab.organizations[0],
        database='default',
    )
    task.run_id = task.next_run_id()
    log.debug("Created task with run_id %s", task.run_id)
    task.save()

    # Create the algorithm runs for this task
    input_ = {
        "master": False,
        "method": "node_online_check",
        "kwargs": {},
        "args": [],
    }
    orgs = collab.organizations
    log.debug("Creating algorithm runs for collaboration %s for %s "
              "organizations", collaboration_id, len(orgs))
    cryptor = DummyCryptor()  # NOTE: OK for this project, not for others!
    for org in orgs:
        serialized_input = pickle.dumps(input_)
        encrypted_input = cryptor.encrypt_bytes_to_str(serialized_input, None)
        result = db.Result(
            task=task,
            organization=org,
            input=encrypted_input,
        )
        result.save()

    log.debug("Emitting new_task event for task %s", task.id)
    # notify nodes a new task available (only to online nodes), nodes that
    # are offline will receive this task on sign in.
    socketio.emit('new_task', task.id, namespace='/tasks',
                  room=f'collaboration_{task.collaboration_id}')

    # wait for nodes to respond
    log.info("Waiting %s seconds for nodes to respond",
             TIME_WAIT_NODE_RESPONSE)
    time.sleep(TIME_WAIT_NODE_RESPONSE)
    log.info("Finished waiting for nodes to respond")

    # update the node status in the database for the nodes that have responded
    task = db.Task.get(task.id)  # refresh task
    for result in task.results:
        if result.started_at is None:
            log.info("Node from organization %s did not respond",
                     result.organization.name)
            # NOTE: we do not set the node status to offline here, because
            # we have not seen issues that nodes have status 'online' while
            # they are not. So this is safer, as it prevents that node that are
            # online but take long to respond are set to offline.
        else:
            log.info("Node from organization %s responded. Setting node status"
                     " online", result.organization.name)
            node = collab.get_node_from_organization(result.organization)
            node.status = 'online'
            node.save()

    # delete the task so that it is not executed when nodes come online later
    log.info("Deleting task %s (node online check)", task.id)
    for result in task.results:
        result.delete()
    task.delete()


def run_for_all_collaborations(socketio):
    """
    Create a task to check which nodes are online for all collaborations.
    """
    # FIXME the below is extremely ugly -> 2 is the id of the starter
    # collaboration. This fix should never make it into another branch.
    collab = db.Collaboration.get(2)
    run(collab.id, socketio)
    # collabs = db.Collaboration.get(2)
    # for collab in collabs:
    #     run(collab.id, socketio)
