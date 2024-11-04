Release notes
=============

4.8.0
-----

* ? November 2024*

- **Feature**

  - Added options ``--ui-image`` and ``--server-image`` to the
    ``v6 dev create-demo-network``
    (`Issue#1518 <https://github.com/vantage6/vantage6/issues/1518>`_,
    `PR#1525 <https://github.com/vantage6/vantage6/pull/1525>`_).
  - Directories can be mounted as databases at the nodes
    (`Issue#1172 <https://github.com/vantage6/vantage6/issues/1172>`_,
    `PR#1540 <https://github.com/vantage6/vantage6/pull/1540>`_).
  - Added retry mechanism for the server database connection on initial connect
    (`Issue#1479 <https://github.com/vantage6/vantage6/issues/1479>`_,
    `PR#1526 <https://github.com/vantage6/vantage6/pull/1526>`_).
  - In case a study is used for an analysis, it is shown in the result page
    (`Issue#1489 <https://github.com/vantage6/vantage6/issues/1489>`_,
    `PR#1561 <https://github.com/vantage6/vantage6/pull/1561>`_).
  - Optional algorithm arguments in the UI
    (`Issue#1219 <https://github.com/vantage6/vantage6/issues/1219>`_,
    `PR#1532 <https://github.com/vantage6/vantage6/pull/1532>`_).
  - Added code of conduct
    (`Issue#1459 <https://github.com/vantage6/vantage6/issues/1459>`_,
    `PR#1480 <https://github.com/vantage6/vantage6/pull/1480>`_).

- **Change**

  - Removed some unused configuration files
    (`Issue#1502 <https://github.com/vantage6/vantage6/issues/1502>`_,
    `PR#1554 <https://github.com/vantage6/vantage6/pull/1554>`_).
  - The API path of the algorithm store is now settable
    (`Issue#1519 <https://github.com/vantage6/vantage6/issues/1519>`_,
    `PR#1524 <https://github.com/vantage6/vantage6/pull/1524>`_).

- **Bugfix**

  - Fixed a buggy seach filter on the task overview page
    (`Issue#1361 <https://github.com/vantage6/vantage6/issues/1361>`_,
    `PR#1561 <https://github.com/vantage6/vantage6/pull/1561>`_)
  - When a node has never been online the status is set to ``ofline`` instead of
    ``None`` (`Issue#1461 <https://github.com/vantage6/vantage6/issues/1461>`_,
    `PR#1552 <https://github.com/vantage6/vantage6/pull/1552>`_).
  - The node support containers are now started with the ``restart-unless-stopped``
    restart policy to prevent them from restarting when the node is shut down in a
    controlled manner (`Issue#1111 <https://github.com/vantage6/vantage6/issues/1111>`_,
    `PR#1553 <https://github.com/vantage6/vantage6/pull/1553>`_).
  - Fixed a bug where the ``server_url`` could not be overruled by the Python client
    or UI. This is used to identify the originating vantage6 server in the algorithm
    store (`Issue#1454 <https://github.com/vantage6/vantage6/issues/1454>`_,
    `PR#1528 <https://github.com/vantage6/vantage6/pull/1528>`_).
  - All fields in the client ``.update`` required to be set, even if they are not
    changed. This is no longer needed
    (`Issue#1515 <https://github.com/vantage6/vantage6/issues/1515>`_,
    `PR#1555 <https://github.com/vantage6/vantage6/pull/1555>`_).
  - Fixed a bug which caused the visualization selection in the result page to reset
    when the computation is complete
    (`Issue#1511 <https://github.com/vantage6/vantage6/issues/1511>`_,
    `PR#1523 <https://github.com/vantage6/vantage6/pull/1523>`_).
  - Users with collaboration edit scope are allowed to reset API keys of nodes from
    all organizations within collaboration the users organization participates in
    (`Issue#1530 <https://github.com/vantage6/vantage6/issues/1530>`_,
    `PR#1529 <https://github.com/vantage6/vantage6/pull/1529>`_).

4.7.1
-----

*1 October 2024*

- **Change**

 - Show nodes in UI on page that shows study
  (`PR#1507 <https://github.com/vantage6/vantage6/pull/1507>`_).
 - Improved viewing/editing your own user in the UI: extra link in top menu, hide
   permissions on edit page because they can't be changed, permission check improvements
  (`PR#1493 <https://github.com/vantage6/vantage6/pull/1493>`_).

- **Bugfix**

 - Improve refreshing task status in UI by fixing permission issue and awaiting task
   collection from the API
   (`Issue#1478 <https://github.com/vantage6/vantage6/issues/1478>`_,
   `PR#1490 <https://github.com/vantage6/vantage6/pull/1490>`_).
 - Prevent corrupt node configuration when specifying ``allowed_algorithms`` in
   ``v6 node new`` (`Issue#1467 <https://github.com/vantage6/vantage6/issues/1467>`_,
   `PR#1468 <https://github.com/vantage6/vantage6/pull/1468>`_).
 - Prevent error in ``v6 node new`` when server URL contains trailing slashes
   (`Issue#1457 <https://github.com/vantage6/vantage6/issues/1457>`_,
   `PR#1468 <https://github.com/vantage6/vantage6/pull/1468>`_).
 - Fix filtering node list when getting nodes for a particular study
   (`Issue#1486 <https://github.com/vantage6/vantage6/issues/1486>`_,
   `PR#1507 <https://github.com/vantage6/vantage6/pull/1507>`_).
 - Only require username or email address in resetting password in Python client
   (`Issue#1503 <https://github.com/vantage6/vantage6/issues/1503>`_,
   `PR#1505 <https://github.com/vantage6/vantage6/pull/1505>`_).
 - Delete study when collaboration is deleted
   (`Issue#1465 <https://github.com/vantage6/vantage6/issues/1465>`_,
   `PR#1487 <https://github.com/vantage6/vantage6/pull/1487>`_).
 - Prevent double policies in the database when multiple algorithm store instances are
   restarted simultaneously (`PR#1506 <https://github.com/vantage6/vantage6/pull/1506>`_).
 - Minor fixes to running tasks in UI: fix repeat task with boolean values, prevent
   submitting same task multiple times, improve showing log file, etc
   (`PR#1490 <https://github.com/vantage6/vantage6/pull/1490>`_).
 - Added missing field and filter options to docstrings in the Python client
   (`PR#1492 <https://github.com/vantage6/vantage6/pull/1492>`_).
 - Prevent error if server is whitelisted at the store for the second time
   (`PR#1491 <https://github.com/vantage6/vantage6/pull/1491>`_).


4.7.0
-----

*20 August 2024*

- **Feature**

 - Added option to delete organizations
   (`Issue#241 <https://github.com/vantage6/vantage6/issues/241>`_,
   `Issue#1120 <https://github.com/vantage6/vantage6/issues/1120>`_,
   `PR#1417 <https://github.com/vantage6/vantage6/pull/1417>`_).
 - Add algorithm store and UI to the ``v6 dev`` network
   (`Issue#1078 <https://github.com/vantage6/vantage6/issues/1078>`_,
   `PR#1399 <https://github.com/vantage6/vantage6/pull/1399>`_).
 - Option to provide hashed password for root user on first server startup, to use
   instead of the default password
   (`Issue#1374 <https://github.com/vantage6/vantage6/issues/1374>`_,
   `PR#1375 <https://github.com/vantage6/vantage6/pull/1375>`_).
 - Improved data included in ``v6 dev`` network so that more tasks can be run on them
   (`PR#1423 <https://github.com/vantage6/vantage6/pull/1423>`_).
 - Added dev policies for algorithm store to enable an algorithm developer to review
   their own algorithm and to disable the review process altogether
   (`Issue#1413 <https://github.com/vantage6/vantage6/issues/1413>`_,
   `PR#1414 <https://github.com/vantage6/vantage6/pull/1414>`_).
 - Added option to delete user to client
   (`PR#1433 <https://github.com/vantage6/vantage6/pull/1433>`_).
 - Added unit tests for algorithm store
   (`Issue#969 <https://github.com/vantage6/vantage6/issues/969>`_,
   `PR#1393 <https://github.com/vantage6/vantage6/pull/1393>`_).
 - Improved algorithm store documentation
   (`Issue#1396 <https://github.com/vantage6/vantage6/issues/1396>`_,
   `PR#1425 <https://github.com/vantage6/vantage6/pull/1425>`_).

- **Change**

 - Apply `node_extra_hosts` confgiruation also to VPN containers
   (`Issue#1355 <https://github.com/vantage6/vantage6/issues/1355>`_,
   `PR#1360 <https://github.com/vantage6/vantage6/pull/1360>`_).
 - Change default port for server from 5000 to 7600 to prevent conflicts with other
   services on Mac (`Issue#1428 <https://github.com/vantage6/vantage6/issues/1428>`_,
   `PR#1429 <https://github.com/vantage6/vantage6/pull/1429>`_).
 - No longer require user to run `client.setup_encryption(None)` if their collaboration
   does not use encryption
   (`Issue#1302 <https://github.com/vantage6/vantage6/issues/1302>`_,
   `PR#1401 <https://github.com/vantage6/vantage6/pull/1401>`_).
 - Improve text in UI task status page (`Issue#1221 <https://github.com/vantage6/vantage6/issues/1221>`_,
   `Issue#1416 <https://github.com/vantage6/vantage6/issues/1416>`_,
   `PR#1419 <https://github.com/vantage6/vantage6/pull/1419>`_).
 - Improve log messages when node is started to let the user know how to view if their
   node is successfully started
   (`Issue#1173 <https://github.com/vantage6/vantage6/issues/1173>`_).
 - Loosened required version of te ``requests`` library in the common package
   (`Issue#1347 <https://github.com/vantage6/vantage6/issues/1353>`_,
   `PR#1405 <https://github.com/vantage6/vantage6/pull/1405>`_).
 - Refactor code that was duplicated between algorithm store and vantage6 server
   (`Issue#1088 <https://github.com/vantage6/vantage6/issues/1088>`_,
   `PR#1415 <https://github.com/vantage6/vantage6/pull/1415>`_).
 - Upgrade UI from Angular 17 to Angular 18
   (`Issue#1347 <https://github.com/vantage6/vantage6/issues/1347>`_,
   `PR#1412 <https://github.com/vantage6/vantage6/pull/1412>`_).
 - No longer print RabbitMQ username/password in server logs
   (`PR#1434 <https://github.com/vantage6/vantage6/pull/1434>`_).

- **Bugfix**

 - No longer require mounting the Docker socket in the algorithm store - which is not
   always possible. Instead, use the OCI spec to get the image digest
   (`PR#1431 <https://github.com/vantage6/vantage6/pull/1431>`_).
 - Fix for when `v6 server remove` crashed because no log file existed - for servers that
   had never been started when they were removed
   (`PR#1432 <https://github.com/vantage6/vantage6/pull/1432>`_).
 - Fix getting the correct algorithm in the UI if multiple stores are linked to a
   collaboration (`Issue#1420 <https://github.com/vantage6/vantage6/issues/1420>`_,
   `PR#1422 <https://github.com/vantage6/vantage6/pull/1422>`_).
 - Fix `v6 dev create` command on MacOS - servers and stores are now created in the
   user folders (`Issue#1408 <https://github.com/vantage6/vantage6/issues/1408>`_,
   `PR#1427 <https://github.com/vantage6/vantage6/pull/1427>`_).
 - Added missing dependency ``pkg_resources``
   (`Issue#1386 <https://github.com/vantage6/vantage6/issues/1386>`_,
   `PR#1418 <https://github.com/vantage6/vantage6/pull/1418>`_).
 - More robust implementation of getting the EduVPN v4 token
   (`PR#1438 <https://github.com/vantage6/vantage6/pull/1438>`_).
 - Upload of algorithm JSON representation in the UI is more resilient to errors
   (`PR#1440 <https://github.com/vantage6/vantage6/pull/1440>`_).

4.6.1
-----

*30 July 2024*

- **Bugfix**

 - Ensure logs will be shown for failed algorithm runs in the UI without the need to
   refresh the page (`PR#1403 <https://github.com/vantage6/vantage6/pull/1403>`_).
 - When creating a task in the UI, dropdown option to select multiple was not properly
   reset when changing selected function from central to partial
   (`PR#1402 <https://github.com/vantage6/vantage6/pull/1402>`_).
 - Fix permission check in UI to show button to register missing nodes
   (`Issue#1230 <https://github.com/vantage6/vantage6/issues/1230>`_,
   `PR#1404 <https://github.com/vantage6/vantage6/pull/1404>`_).
 - Pass on ``print_log_header`` argument when running ``v6 node stop`` to prevent entire
   log header to be printed (`Issue#1398 <https://github.com/vantage6/vantage6/issues/1398>`_,
   `PR#1400 <https://github.com/vantage6/vantage6/pull/1400>`_).
 - Add missing docker dependency to algorithm store
   (`PR#1409 <https://github.com/vantage6/vantage6/pull/1409>`_).

4.6.0
-----

*17 July 2024*

- **Feature**

 - Added option ``allowed_algorithm_stores`` to node configuration. This option allows
   node administrators to allow all approved algorithms from a specific algorithm store
   to be run on their node (`Issue#1293 <https://github.com/vantage6/vantage6/issues/1293>`_,
   `PR#1318 <https://github.com/vantage6/vantage6/pull/1318>`_).
 - Added policy management system to the algorithm store, and implemented a first few
   policies, e.g. to control who can view and run algorithms
   (`Issue#1026 <https://github.com/vantage6/vantage6/issues/1026>`_,
   `PR#1299 <https://github.com/vantage6/vantage6/pull/1299>`_).
 - Implemented review process in the algorithm store. Algorithms now need to be reviewed
   by at least one other user before they are published in the store
   (`Issue#981 <https://github.com/vantage6/vantage6/issues/981>`_,
   `PR#1358 <https://github.com/vantage6/vantage6/pull/1358>`_).
 - Option to visualize line charts in the UI
   (`Issue#1324 <https://github.com/vantage6/vantage6/issues/1324>`_,
   `PR#1330 <https://github.com/vantage6/vantage6/pull/1330>`_).
 - Users and permissions of the algorithm store can now be managed in the UI
   (`Issue#1123 <https://github.com/vantage6/vantage6/issues/1123>`_,
   `PR#1340 <https://github.com/vantage6/vantage6/pull/1340>`_).
 - Support default pandas ``DataFrame.to_json()`` output to visualize table in UI
   (`PR#1331 <https://github.com/vantage6/vantage6/pull/1331>`_).
 - Create option for node administrator to enforce that new algorithm image is
   successfully pulled before running a task with it
   (`Issue#1200 <https://github.com/vantage6/vantage6/issues/1200>`_,
   `PR#1344 <https://github.com/vantage6/vantage6/pull/1344>`_).
 - Show more clearly in the UI when node has last been seen online
   (`Issue#1308 <https://github.com/vantage6/vantage6/issues/1308>`_,
   `PR#1343 <https://github.com/vantage6/vantage6/pull/1343>`_).
 - Option in creating tasks to indicate which algorithm store the algorithm should be
   obtained from (`Issue#1198 <https://github.com/vantage6/vantage6/issues/1198>`_,
   `PR#1318 <https://github.com/vantage6/vantage6/pull/1318>`_).

- **Change**

 - As EduVPN v2 is no longer supported on modern systems, vantage6 now supports EduVPN
   v3 instead of v2 (`Issue#1180 <https://github.com/vantage6/vantage6/issues/1180>`_,
   `PR#1345 <https://github.com/vantage6/vantage6/pull/1345>`_).
 - Improved the server - algorithm store whitelisting process
   (`Issue#1177 <https://github.com/vantage6/vantage6/issues/1177>`_,
   `Issue#1178 <https://github.com/vantage6/vantage6/issues/1178>`_,
   `PR#1299 <https://github.com/vantage6/vantage6/pull/1299>`_).
 - Removed `connectorx` dependency due to issues with installing it. Instead, using
   SQLAlchemy to read SQL queries in the SQL wrapper
   (`PR#1385 <https://github.com/vantage6/vantage6/pull/1385>`_).
 - Make it possible to run infrastructure components with local images
   (`Issue#1250 <https://github.com/vantage6/vantage6/issues/1250>`_,
   `PR#1332 <https://github.com/vantage6/vantage6/pull/1332>`_).
 - Make `node_extra_hosts` also available to VPN client container
   (`Issue#1355 <https://github.com/vantage6/vantage6/issues/1355>`_,
   `PR#1360 <https://github.com/vantage6/vantage6/pull/1360>`_).
 - Documented algorithm store permission system
   (`Issue#1086 <https://github.com/vantage6/vantage6/issues/1086>`_,
   `PR#1354 <https://github.com/vantage6/vantage6/pull/1354>`_).

- **Bugfix**

 - Fix filling in JSON and list parameters when repeating task in the UI
   (`PR#1328 <https://github.com/vantage6/vantage6/pull/1328>`_).
 - Added `always_connect` option to socketIO connection to prevent random `BadNameSpace`
   errors (`Issue#1333 <https://github.com/vantage6/vantage6/issues/1333>`_,
   `PR#1334 <https://github.com/vantage6/vantage6/pull/1334>`_).
 - Verify that user exists before assigning it permission in the algorithm store
   (`Issue#1092 <https://github.com/vantage6/vantage6/issues/1092>`_,
   `PR#1299 <https://github.com/vantage6/vantage6/pull/1299>`_).

4.5.5
-----

*13 June 2024*

- **Bugfix**

 - Fix faulty environment variable check in the OHDSI database connector
   (`PR#1326 <https://github.com/vantage6/vantage6/pull/1326>`_)

4.5.4
-----

*13 June 2024*

- **Change**

 - Changed default role 'Collaboration admin' so that they can no longer create new
   collaborations: this was deemed too powerful for this role
   (`PR#1313 <https://github.com/vantage6/vantage6/pull/1313>`_).

- **Bugfix**

 - Prevent SSL errors in communication between server and algorithm store due to wrong
   order imports with monkey patch (`Issue#1311 <https://github.com/vantage6/vantage6/issues/1311>`_,
   `PR#1320 <https://github.com/vantage6/vantage6/pull/1320>`_).
 - Fix forwarding of custom headers to algorithm store when communicating from the
   vantage6 server (`PR#1298 <https://github.com/vantage6/vantage6/pull/1298>`_).


4.5.3
-----

*6 June 2024*

- **Bugfix**

 - Included `__build__` file of algorithm tools in the PyPI package to prevent error
   when using the package (`PR#1307 <https://github.com/vantage6/vantage6/pull/1307>`_).

4.5.2
-----

*3 June 2024*

- **Bugfix**

 - Updated PyPI Docker dependency to 7.1.0 and requests to 2.32.3 to fix issues with
   ``docker.from_env()`` with old combination of docker/requests
   (`PR#1306 <https://github.com/vantage6/vantage6/pull/1306>`_).


4.5.1
-----

*3 June 2024*

- **Change**

 - Make ``__version__`` attribute available for each vantage6 package
   (`PR#1303 <https://github.com/vantage6/vantage6/pull/1303>`_).
 - Update ``requests`` dependency to 2.32.2 (`PR#1294 <https://github.com/vantage6/vantage6/pull/1294>`_).


- **Bugfix**

 - Added missing ``connectorx`` dependency (`PR#1301 <https://github.com/vantage6/vantage6/pull/1301>`_).
 - Fix readthedocs build error (`PR#1295 <https://github.com/vantage6/vantage6/pull/1295>`_).

4.5.0
-----

*23 May 2024*

- **Security**

 - Prevent that a collaboration admin extends their own permissions by expanding the
   collaboration (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-99r4-cjp4-3hmx>`_,
   `commit <https://github.com/vantage6/vantage6/commit/27f4ee3fade5f4cbcf3e60899c9a2a91145e0b56>`_).

- **Feature**

 - Visualization and management of algorithms in the UI
   (`Issue#1115 <https://github.com/vantage6/vantage6/issues/1115>`_,
   `PR#1261 <https://github.com/vantage6/vantage6/pull/1261>`_).
 - Support encryption and decryption of results and task input in the UI
   (`Issue#1140 <https://github.com/vantage6/vantage6/issues/1140>`_,
   `PR#1248 <https://github.com/vantage6/vantage6/pull/1248>`_).
 - Added client function ``client.algorithm.update()`` to update store algorithms
   (`Issue#1089 <https://github.com/vantage6/vantage6/issues/1089>`_,
   `PR#1277 <https://github.com/vantage6/vantage6/pull/1277>`_).
 - Pass ``dbms`` environment variable to algorithm for OMOP connections
   (`Issue#1036 <https://github.com/vantage6/vantage6/issues/1036>`_,
   `PR#1267 <https://github.com/vantage6/vantage6/pull/1267>`_).
 - Improved error message in client when wrong API path is provided
   (`Issue#1001 <https://github.com/vantage6/vantage6/issues/1001>`_,
   `PR#1252 <https://github.com/vantage6/vantage6/pull/1252>`_).

- **Change**

 - Default logging level changed from ``debug`` to ``info``
   (`Issue#692 <https://github.com/vantage6/vantage6/issues/692>`_,
   `PR#1216 <https://github.com/vantage6/vantage6/pull/1216>`_).
 - Don't send column names request for OMOP and other databases
   (`Issue#1117 <https://github.com/vantage6/vantage6/issues/1117>`_,
   `PR#1272 <https://github.com/vantage6/vantage6/pull/1272>`_).
 - Function documentation generated with Sphinx autosummary
   (`PR#1279 <https://github.com/vantage6/vantage6/pull/1279>`_).
 - New error classes and extra functionality for getting environment variables in the
   algorithm tools (`PR#1226 <https://github.com/vantage6/vantage6/pull/1226>`_).
 - Improved codacy and DOI badges in README (`PR#1271 <https://github.com/vantage6/vantage6/pull/1271>`_).
 - Unpin uWSGI version which was fixed to mitigate a build issue with a previous latest
   version of uWSGI
   (`Issue#1208 <https://github.com/vantage6/vantage6/issues/1208>`_,
   `PR#1217 <https://github.com/vantage6/vantage6/pull/1217>`_).

- **Bugfix**

 - Ensure button to register missing nodes does not show up when all nodes have been
   registered (`Issue#1229 <https://github.com/vantage6/vantage6/issues/1229>`_,
   `PR#1225 <https://github.com/vantage6/vantage6/pull/1225>`_).
 - Prevent returning wrong status code by proxy server when creating subtasks
   (`Issue#1241 <https://github.com/vantage6/vantage6/issues/1241>`_,
   `PR#1268 <https://github.com/vantage6/vantage6/pull/1268>`_).
 - In UI, when resetting password, fix check that the users enters the same new password
   twice (`Issue#1228 <https://github.com/vantage6/vantage6/issues/1228>`_,
   `PR#1256 <https://github.com/vantage6/vantage6/pull/1256>`_).
 - In UI, fix console errors when repeating a task
   (`Issue#1125 <https://github.com/vantage6/vantage6/issues/1125>`_,
   `PR#1261 <https://github.com/vantage6/vantage6/pull/1261>`_).
 - Fix error with undefined variable in deleting docker volumes
   (`Issue#1263 <https://github.com/vantage6/vantage6/issues/1263>`_,
   `PR#1264 <https://github.com/vantage6/vantage6/pull/1264>`_).
 - Fixed an error in the ``MockClient`` that modified local mock data is shared with
   subsequent calls
   (`PR#1284 <https://github.com/vantage6/vantage6/pull/1284>`_).

4.4.1
-----

*8 May 2024*

- **Security**

 - Updated dependencies Werkzeug to 3.0.3 and Jinja2 to 3.1.4

- **Change**

 - When columns cannot be retrieved in the UI when creating a task, give the user the
   option to fill in column names manually
   (`PR#1212 <https://github.com/vantage6/vantage6/pull/1212>`_).

- **Bugfix**

 - Updated PyYAML dependency to 6.0.1 to allow building on Python 3.12
   (`PR#1233 <https://github.com/vantage6/vantage6/pull/1233>`_).


4.4.0
-----

*15 April 2024*

- **Feature**

 - Added visualization of a results table to the UI. The algorithm store is used to
   store how the table should be visualized.
   (`Issue#1057 <https://github.com/vantage6/vantage6/issues/1057>`_,
   `PR#1195 <https://github.com/vantage6/vantage6/pull/1195>`_).
 - Support for more types of algorithm arguments via the UI: lists of strings, ints,
   floats and columns, and booleans
   (`Issue#1119 <https://github.com/vantage6/vantage6/issues/1119>`_,
   `PR#1190 <https://github.com/vantage6/vantage6/pull/1190>`_).
 - Added configuration option to link algorithm stores to a server via the server
   configuration (`PR#1156 <https://github.com/vantage6/vantage6/pull/1156>`_).
 - Added a bunch of custom exceptions for algorithms to the algorithm tools
   (`Issue#1185 <https://github.com/vantage6/vantage6/issues/1185>`_,
   `PR#1205 <https://github.com/vantage6/vantage6/pull/1205>`_).
 - Decoding the environment variables automatically in the algorithm wrapper, to prevent
   that a user has to decode them manually
   (`Issue#1056 <https://github.com/vantage6/vantage6/issues/1056>`_,
   `PR#1197 <https://github.com/vantage6/vantage6/pull/1197>`_).
 - Add option to delete roles in the UI
   (`Issue#1113 <https://github.com/vantage6/vantage6/issues/1113>`_,
   `PR#1199 <https://github.com/vantage6/vantage6/pull/1199>`_).
 - Add option to register a node in the UI *after* creating/editing the collaboration
   (`Issue#1122 <https://github.com/vantage6/vantage6/issues/1122>`_,
   `PR#1202 <https://github.com/vantage6/vantage6/pull/1202>`_).

- **Change**

 - Updated idna dependency

- **Bugfix**

 - Do not mark algorithm runs as killed if they were completed before the user killed
   the task to which the runs belong
   (`Issue#1045 <https://github.com/vantage6/vantage6/issues/1045>`_,
   `PR#1204 <https://github.com/vantage6/vantage6/pull/1204>`_).
 - Fix UI code in a few places where pagination was not implemented properly
   (`Issue#1126 <https://github.com/vantage6/vantage6/issues/1126>`_,
   `PR#1203 <https://github.com/vantage6/vantage6/pull/1203>`_).

4.3.4
-----

*09 April 2024*


- **Security**

 - Updated express dependency in UI to 4.19.2

- **Feature**

 - Added option to add hostname mappings in the node configuration
   (`Issue#1094 <https://github.com/vantage6/vantage6/issues/1094>`_,
   `PR#1167 <https://github.com/vantage6/vantage6/pull/1167>`_).

- **Change**

 - Always pull new Docker images instead of checking timestamps and only pulling
   image if the remote image is newer
   (`Issue#1188 <https://github.com/vantage6/vantage6/issues/1188>`_,
   `Issue#1105 <https://github.com/vantage6/vantage6/issues/1105>`_,
   `PR#1169 <https://github.com/vantage6/vantage6/pull/1189>`_).
 - Changed behaviour of ``v6 algorithm update`` to skip previously-answered questions
   by default, and added flag that allows changing them. Also added flag to allow using
   a Python script in the updated copier template
   (`PR#1176 <https://github.com/vantage6/vantage6/pull/1176>`_).

- **Bugfix**

 - Fix encoding of non-string algorithm environment variables by casting them to string
   (`PR#1186 <https://github.com/vantage6/vantage6/pull/1186>`_).
 - Fix bug in algorithm client: only send study ID when it is defined
   (`PR#1184 <https://github.com/vantage6/vantage6/pull/1184>`_).
 - Update copier dependency which was causing a CLI error
   (`PR#1187 <https://github.com/vantage6/vantage6/pull/1187>`_).

4.3.3
-----

*25 March 2024*


- **Change**

 - Improved integration algorithm store in UI (`PR#1163 <https://github.com/vantage6/vantage6/pull/1163>`_).
 - Improve picking an online node when creating task in the UI: pick one that shares
   configuration and give more specific information to the user in case certain data
   could not be retrieved (`PR#1164 <https://github.com/vantage6/vantage6/pull/1164>`_).
 - UI dependency updates

- **Bugfix**

 - Fix pulling algorithms from registries that require authentication
   (`Issue#1168 <https://github.com/vantage6/vantage6/issues/1168>`_,
   `PR#1169 <https://github.com/vantage6/vantage6/pull/1169>`_).
 - Fix bug in showing create task button in UI
   (`PR#1165 <https://github.com/vantage6/vantage6/pull/1165>`_).
 - Could not view studies with collaboration scope permissions
   (`Issue#1154 <https://github.com/vantage6/vantage6/issues/1154>`_,
   `PR#1157 <https://github.com/vantage6/vantage6/pull/1157>`_).
 - Fix bug when viewing algorithm stores with organization scope permissions
   (`PR#1159 <https://github.com/vantage6/vantage6/pull/1159>`_).
 - Detect whitelisted server in algorithm store if port ``443`` or ``80`` at the end
   of the URL is the only difference with the whitelisted URL
   (`Issue#1155 <https://github.com/vantage6/vantage6/issues/1155>`_,
   `PR#1162 <https://github.com/vantage6/vantage6/pull/1162>`_).
 - Better error message in Python client when trying to send requests to algorithm store
   when it has not yet been set up (`Issue#1134 <https://github.com/vantage6/vantage6/issues/1153>`_,
   `PR#1158 <https://github.com/vantage6/vantage6/pull/1158>`_).

4.3.2
-----

*20 March 2024*


- **Change**

 - Integrated user interface in main repository
   `PR#1112 <https://github.com/vantage6/vantage6/pull/1112>`_).

- **Bugfix**

 - Allow usernames to contain dots and don't apply username validation to login
   endpoints until v5 to allow existing users to login
   (`PR#1148 <https://github.com/vantage6/vantage6/pull/1148>`_).

4.3.1
-----

*18 March 2024*


- **Feature**

 - New configuration option to set a server name in the server configuration file, which
   will be used to identify the server in a two-factor app.
   (`Issue#1016 <https://github.com/vantage6/vantage6/issues/1016>`_,
   `PR#1075 <https://github.com/vantage6/vantage6/pull/1075>`_).

- **Change**

 - Allow user with organization scope permission to view studies to retrieve studies
   for a particular collaboration, even though they may not be able to view them all
   (`PR#1104 <https://github.com/vantage6/vantage6/pull/1104>`_).
 - Add option to set policies on openness of algorithm viewing in algorithm store
   to configuration wizard (`PR#1106 <https://github.com/vantage6/vantage6/pull/1106>`_).
 - Improved help text in UI in several places and show the username in the top right
   (`PR#254 <https://github.com/vantage6/vantage6-UI/pull/254>`_,
   `PR#257 <https://github.com/vantage6/vantage6-UI/pull/257>`_)

- **Bugfix**

 - Update default roles on server startup if they have changed. This may happen on
   minor version updates (`Issue#1102 <https://github.com/vantage6/vantage6/issues/1102>`_,
   `PR#1103 <https://github.com/vantage6/vantage6/pull/1103>`_).
 - Update selected collaboration in the UI when it is updated in the administration
   section (`PR#253 <https://github.com/vantage6/vantage6-UI/pull/253>`_)
 - Fix showing the create task button if user has no global permissions
   (`PR#259 <https://github.com/vantage6/vantage6-UI/pull/259>`_)
 - Remove wrong message for CORS not functioning properly with default settings
   (`PR#1107 <https://github.com/vantage6/vantage6/pull/1107>`_).

4.3.0
-----

*12 March 2024*

- **Security**

 - Implemented configuration option to set CORS origins on the central server. This may
   be used to further enhance the security profile of your server
   (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-4946-85pr-fvxh>`_,
   `commit <https://github.com/vantage6/vantage6/commit/70bb4e1d889230a841eb364d6c03accd7dd01a41>`_).
 - Prevent username enumeration attack on endpoints where password and 2FA are reset
   (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-5h3x-6gwf-73jm>`_,
   `commit <https://github.com/vantage6/vantage6/commit/aecfd6d0e83165a41a60ebd52d2287b0217be26b>`_).
 - Added HTTP security headers on the user interface to provide an additional layer
   of security to help mitigate attacks and vulnerabilites
   (`advisory <https://github.com/vantage6/vantage6-UI/security/advisories/GHSA-gwq3-pvwq-4c9w>`_,
   `commit <https://github.com/vantage6/vantage6-UI/commit/68dfa661415182da0e5717bd58db3d00aedcbd2e>`_).
 - Updated cryptography dependency

- **Feature**

 - New user interface. The new UI is a complete rewrite of the old UI and is
   more focused on facilitating the researcher in running tasks and viewing their
   progress and results (`PR#930 <https://github.com/vantage6/vantage6-UI/pull/246>`_).
 - New infrastructure component: the algorithm store. The algorithm store is a place
   to make algorithms easily findable and easier to run. Algorithm stores can be
   made available to specific collaborations or to all collaborations in an entire
   vantage6 server. By doing so, the new UI will automatically pick up these algorithms
   and guide the user through running analyses with them (
   `Issue#911 <https://github.com/vantage6/vantage6/issues/911>`_,
   `PR#1048 <https://github.com/vantage6/vantage6/pull/1004>`_ and several other PRs)
 - Introducing 'study' concept. A study is essentially a 'sub-collaboration', where
   a subset of organizations of the collaboration can work together on a specific
   research question. Tasks and results are then easily grouped together for the study
   (`Issue#812 <https://github.com/vantage6/vantage6/issues/812>`_,
   `PR#1069 <https://github.com/vantage6/vantage6/pull/1069>`_).
 - Add flag whether role is default or not
   (`Issue#949 <https://github.com/vantage6/vantage6/issues/949>`_,
   `PR#1063 <https://github.com/vantage6/vantage6/pull/1063>`_).
 - Report username/password combination at the end of the logs when it is created
   (`Issue#830 <https://github.com/vantage6/vantage6/issues/830>`_,
   `PR#1041 <https://github.com/vantage6/vantage6/pull/1041>`_).


- **Change**

 - Introducing new package ``vantage6-backend-common`` for code that is shared between
   the central server and the algorithm store
   (`Issue#979 <https://github.com/vantage6/vantage6/issues/979>`_,
   `PR#1037 <https://github.com/vantage6/vantage6/pull/1037>`_).
 - Show the default values for CLI commands when displaying the help text
   (`Issue#1000 <https://github.com/vantage6/vantage6/issues/1000>`_,
   `PR#1070 <https://github.com/vantage6/vantage6/pull/1070>`_).
 - Setting the allowed algorithms is now part of the questionnaire on node setup
   (`PR#1046 <https://github.com/vantage6/vantage6/pull/1046>`_).
 - Usernames are now required to be at least three characters long and contain only
   roman letters, numbers, and the characters '_' and '-'
   (`PR#1060 <https://github.com/vantage6/vantage6/pull/1060>`_).
 - Remove OMOP wrapper since we now have specific connectors to connect to this database
   type and wrapper was therefore not used
   (`Issue#1002 <https://github.com/vantage6/vantage6/issues/1002>`_,
   `PR#1067 <https://github.com/vantage6/vantage6/pull/1067>`_).
 - ``v6 node`` commands no longer require full path when using the ``--config`` option
   (`Issue#870 <https://github.com/vantage6/vantage6/issues/870>`_,
   `PR#1042 <https://github.com/vantage6/vantage6/pull/1042>`_).
 - Apply black code formatting to the entire repository
   (`Issue#968 <https://github.com/vantage6/vantage6/issues/968>`_,
   `PR#1012 <https://github.com/vantage6/vantage6/pull/1012>`_).
 - Remove option to update organization or collaboration of an existing node. Preferred
   workflow in that case is to delete and re-create it. Also add option ``clear_ip`` to
   clear the VPN IP address of the node
   (`PR#1053 <https://github.com/vantage6/vantage6/pull/1053>`_).

- **Bugfix**

 - Fix VPN network cleanup if ``iptables-legacy`` is installed, and improve cleanup of
   the node's containers, volumes and networks when the node is stopped
   (`Issue#1058 <https://github.com/vantage6/vantage6/issues/1058>`_,
   `PR#1059 <https://github.com/vantage6/vantage6/pull/1059>`_).
 - Prevent logger thread to crash on input that it cannot read
   (`Issue#879 <https://github.com/vantage6/vantage6/issues/879>`_,
   `PR#1043 <https://github.com/vantage6/vantage6/pull/1043>`_).
 - Fixed setting up VPN network on Ubuntu 22.04
   (`Issue#724 <https://github.com/vantage6/vantage6/issues/724>`_,
   `PR#1044 <https://github.com/vantage6/vantage6/pull/1044>`_).

4.2.3
-----

*21 February 2024*

- **Security**

    - Updated ``cryptography`` dependency to version ``42.0.2``
      (`PR#1047 <https://github.com/vantage6/vantage6/pull/1047>`_,
      `PR#1048 <https://github.com/vantage6/vantage6/pull/1048>`_).

- **Feature**

    - Added the option to specify a private key file when using the
      ``v6 test feature-test`` command
      (`Issue#1018 <https://github.com/vantage6/vantage6/issues/1018>`_,
      `PR#1019 <https://github.com/vantage6/vantage6/pull/1019>`_).

- **Bugfix**

     - Using the whitelisting feature without VPN prevented algorithm containers from
       starting (`PR#1055 <https://github.com/vantage6/vantage6/pull/1055>`_)
     - Shutting down the node did not properly remove all containers, volumes and
       networks (`PR#1059 <https://github.com/vantage6/vantage6/pull/1059>`_).

4.2.2
-----

*26 January 2024*

- **Feature**

 - Configuration options for the node to add extra mounts and extra environment
   variables for the node itself
   (`Issue#961 <https://github.com/vantage6/vantage6/issues/961>`_,
   `PR#963 <https://github.com/vantage6/vantage6/pull/963>`_).

- **Change**

 - The entire repository is now formatted with Black code style. Additionally,
   a pipeline was added to check this for new PRs and commit hooks are provided
   for developers (`PR#992 <https://github.com/vantage6/vantage6/pull/992>`_).
 - When the ``PKG_NAME`` environeent variable was not set in the Dockerfile,
   a clear error is now raised
   (`Issue#995 <https://github.com/vantage6/vantage6/issues/995>`_,
   `PR#1010 <https://github.com/vantage6/vantage6/pull/1010>`_).

- **Bugfix**

 - Running encrypted algorithms failed due to a bug in the proxy server
   (`Issue#955 <https://github.com/vantage6/vantage6/issues/955>`_,
   `PR#1008 <https://github.com/vantage6/vantage6/pull/1008>`_).
 - Node logs were not persisted properly. This has been fixed
   (`Issue#993 <https://github.com/vantage6/vantage6/issues/993>`_,
   `PR#1009 <https://github.com/vantage6/vantage6/pull/1009>`_).

4.2.1
-----

*19 January 2024*

- **Bugfix**
 - Add back binary installation of ``psycopg2`` to support Postgres databases
   (`PR#932 <https://github.com/vantage6/vantage6/pull/932>`_).

4.2.0
-----

*18 January 2024*

- **Security**

 - Remove option to SSH into node and server containers. The configuration was
   not completely secure
   (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-2wgc-48g2-cj5w>`_,
   `commit <https://github.com/vantage6/vantage6/commit/3fcc6e6a8bd1142fd7a558d8fdd2b246e55c8841>`_).
 - Prevent code injection into environment variables
   (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-w9h2-px87-74vx>`_,
   `commit <https://github.com/vantage6/vantage6/commit/eac19db737145d3ca987adf037a454fae0790ddd>`_).
 - Prevent that user can accidentally upload non-encrypted input to the server
   for an encrypted collaboration.
   (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-rjmv-52mp-gjrr>`_,
   `commit <https://github.com/vantage6/vantage6/commit/6383283733b81abfcacfec7538dc4dc882e98074>`_).
 - Prevent that usernames are findable in brute force attack due to a difference
   in response time when they exist versus when they don't exist
   (`advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-45gq-q4xh-cp53>`_,
   `commit <https://github.com/vantage6/vantage6/commit/389f416c445da4f2438c72f34c3b1084485c4e30>`_).
 - Updated dependencies of jinja2, cryptography and Werkzeug. (
   `PR#984 <https://github.com/vantage6/vantage6/pull/984>`_).

- **Feature**

 - Introduced the ``v6 test`` commands that will run the test algorithm
   ``v6-diagnostics`` (`Issue#918 <https://github.com/vantage6/vantage6/issues/918>`_,
   `PR#930 <https://github.com/vantage6/vantage6/pull/930>`_).
 - Extended ``v6 dev`` commands with options to add extra configuration to the
   server and node configuration files. Also, added the ``v6 server remove``
   command. (`Issue#860 <https://github.com/vantage6/vantage6/issues/860>`_,
   `PR#930 <https://github.com/vantage6/vantage6/pull/930>`_).

- **Change**

 - Changed some log messages to a more appropriate log level
   (`Issue#667 <https://github.com/vantage6/vantage6/issues/667>`_)
 - Improved message when node starts so as to make it clearer to users that
   the node has not yet authenticated
   (`PR#957 <https://github.com/vantage6/vantage6/pull/957>`_).
 - Changed socket event ``on_new_task`` to also include the parent ID of the
   task that was created (`PR#950 <https://github.com/vantage6/vantage6/pull/950>`_).

- **Bugfix**

 - Added check whether database labels are properly specified when creating a
   task (`Issue#910 <https://github.com/vantage6/vantage6/issues/910>`_,
   `PR#932 <https://github.com/vantage6/vantage6/pull/932>`_).
 - Fix bug in creating task with VPN client image when it has ``iptables-legacy``
   installed (`Issue#966 <https://github.com/vantage6/vantage6/issues/966>`_,
   `PR#982 <https://github.com/vantage6/vantage6/pull/982>`_).
 - Add missing ``email`` argument from ``client.user.create`` function
   (`Issue#837 <https://github.com/vantage6/vantage6/issues/837>`_,
   `PR#934 <https://github.com/vantage6/vantage6/pull/934>`_).

4.1.3
-----

*19 December 2023*

- **Bugfix**

 - Server logs were not persisted properly
   (`Issue#951 <https://github.com/vantage6/vantage6/issues/951>`_,
   `PR#953 <https://github.com/vantage6/vantage6/pull/953>`_).
 - Fixed validation of request to recover two-factor authentication secret
   (`PR#941 <https://github.com/vantage6/vantage6/pull/941>`_).
 - Default roles were visible via GET ``/role`` but not via GET ``/role/<id>``
   for users without global role view permission. Now they are visible via both
   (`PR#948 <https://github.com/vantage6/vantage6/pull/948>`_).


4.1.2
-----

*14 November 2023*

- **Security**

 - Improved check which algorithms are allowed - no longer trusting an algorithm
   with a `parent_id` by default (
   `advisory <https://github.com/vantage6/vantage6/security/advisories/GHSA-vc3v-ppc7-v486>`_,
   `commit <https://github.com/vantage6/vantage6/commit/92159580f11a17cd2e06f73f636088bbcbfe9cbc>`_).

4.1.1
-----

*1 November 2023*

- **Bugfix**

 - Added OpenPyxl dependency to algorithm tools which is required to read Excel
   databases (`PR#923 <https://github.com/vantage6/vantage6/pull/923>`_).
 - Explicitly define the resource on which sorting is done in the API. This
   prevents SQL errors when SQLAlchemy tries to sort on a column in a joined
   table (`PR#925 <https://github.com/vantage6/vantage6/pull/925>`_).
 - Fixed retrieving column names for Excel databases
   (`PR#924 <https://github.com/vantage6/vantage6/pull/924>`_).

4.1.0
-----

*19 October 2023*

- **Feature**

 - Renamed CLI commands. The new commands are:

   - ``vnode`` → ``v6 node``
   - ``vserver`` → ``v6 server``
   - ``vdev`` → ``v6 dev``

   The old commands will still be available until version 5.0 is released.
 - Added CLI command ``v6 algorithm create`` which is a starting point for
   creating new algorithms
   (`Issue#400 <https://github.com/vantage6/vantage6/issues/400>`_,
   `PR#904 <https://github.com/vantage6/vantage6/pull/904>`_).
 - Added ``@database_connection(type_)`` algorithm decorator. This enables
   algorithm developers to inject a database connection into their algorithm
   instead of a dataframe. The only type that currently is support is ``omop``,
   which injects a ``OHDSI/DatabaseConnection`` object into your algorithm.
   (`PR#902 <https://github.com/vantage6/vantage6/pull/902>`_).
 - Added endpoint `/column` for the UI to get the column names of the database.
   This is achieved either by sharing column names by the node for file-based
   databases or by sending a task using the ``basics`` algorithm. The latter
   is now an allowed algorithm by default, unless the node is configured to
   not allow it. ((`Issue#778 <https://github.com/vantage6/vantage6/issues/778>`_,
   `PR#908 <https://github.com/vantage6/vantage6/pull/908>`_).
 - Added ``only_siblings`` and ``only_self`` options to the
   ``client.vpn.get_addresses`` function. These options allow you to get the
   VPN addresses of only the siblings or only the node itself, respectively.
   This is useful for algorithms that need to communicate with other
   algorithms on the same node or with the node itself.
   (`Issue#729 <https://github.com/vantage6/vantage6/issues/729>`_,
   `PR#901 <https://github.com/vantage6/vantage6/pull/901>`_).

4.0.3
-----

*16 October 2023*

- **Bugfix**

 - Fix where custom Docker image for node was defined in config file but not
   used in practice (`PR#896 <https://github.com/vantage6/vantage6/pull/896>`_).
 - Fixed getting VPN algorithm addresses from ``AlgorithmClient``
   (`PR#898 <https://github.com/vantage6/vantage6/pull/898>`_).

4.0.2
-----

*9 October 2023*

- **Bugfix**

 - Fix socket connection from node to server due to faulty callback, which
   occurred when server was deployed. This bug was introduced in v4.0.1
   (`PR#892 <https://github.com/vantage6/vantage6/pull/892>`_).

4.0.1
-----

*5 October 2023*

- **Security**

 - Updating dependencies ``cryptography``, ``gevent``, and ``urllib3`` to fix
   vulnerabilities (`PR#889 <https://github.com/vantage6/vantage6/pull/889>`_)

- **Bugfix**

 - Fix node connection issues if server without constant JWT secret key is
   restarted (`Issue#840 <https://github.com/vantage6/vantage6/issues/840>`_,
   `PR#866 <https://github.com/vantage6/vantage6/pull/866>`_).
 - Improved algorithm_client decorator with ``@wraps`` decorator. This fixes
   an issue with the data decorator in the AlgorithmMockClient
   (`Issue#874 <https://github.com/vantage6/vantage6/issues/874>`_,
   `PR#882 <https://github.com/vantage6/vantage6/pull/882>`_).
 - Decoding the algorithm results and algorithm input has been made more robust,
   and input from ``vserver import`` is now properly encoded
   (`Issue#836 <https://github.com/vantage6/vantage6/issues/836>`_,
   `PR#864 <https://github.com/vantage6/vantage6/pull/864>`_).
 - Improve error message if user forgot to specify ``databases`` when creating a
   task (`Issue#854 <https://github.com/vantage6/vantage6/issues/854>`_,
   `PR#865 <https://github.com/vantage6/vantage6/pull/865>`_).
 - Fix data loading in AlgorithmMockClient
   (`Issue#872 <https://github.com/vantage6/vantage6/issues/872>`_,
   `PR#881 <https://github.com/vantage6/vantage6/pull/881>`_).

4.0.0
-----

*20 September 2023*

- **Security**

 - No longer using Python pickles for serialization and deserialization of
   algorithm results. Using JSON instead (
   `CVE#CVE-2023-23930 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-23930>`_,
   `commit <https://github.com/vantage6/vantage6/commit/e62f03bacf2247bd59eed217e2e7338c3a01a5f0>`_).
 - Not allowing resources to have an integer name (
   `CVE#CVE-2023-28635 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-28635>`_,
   `PR#744 <https://github.com/vantage6/vantage6/pull/744>`_).
 - Users allowed to view collaborations but not allowed to view tasks may be
   able to view them via ``/api/collaboration/<id>/task`` (
   `CVE#CVE-2023-41882 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-41882>`_,
   `PR#741 <https://github.com/vantage6/vantage6/pull/741>`_).
 - Users allowed to view tasks but not results may be able to view them via
   ``/api/task?include=results`` (
   `CVE#CVE-2023-41882 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-41882>`_,
   `PR#711 <https://github.com/vantage6/vantage6/pull/711>`_).
 - Deleting all linked tasks when a collaboration is deleted (
   `CVE#CVE-2023-41881 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-41881>`_,
   `PR#748 <https://github.com/vantage6/vantage6/pull/748>`_).

- **Feature**

 - A complete permission scope has been added at the collaboration level,
   allowing projects to assign one user to manage everything within that
   collaboration level without requiring global access
   (`Issue#245 <https://github.com/vantage6/vantage6/issues/245>`_,
   `PR#711 <https://github.com/vantage6/vantage6/pull/711>`_).
 - Added decorators ``@algorithm_client`` and ``@data()`` to make the signatures
   and names of algorithm functions more flexible and also to allow for multiple
   databases (`Issue#440 <https://github.com/vantage6/vantage6/issues/440>`_,
   `PR#652 <https://github.com/vantage6/vantage6/pull/652>`_).
 - Allow a single algorithm function to make use of multiple databases
   (`Issue#804 <https://github.com/vantage6/vantage6/issues/804>`_,
   `PR#652 <https://github.com/vantage6/vantage6/pull/652>`_,
   `PR#807 <https://github.com/vantage6/vantage6/pull/807>`_).
 - Enforce pagination in the API to improve performance, and add a `sort`
   parameter for GET requests which yield multiple resources
   (`Issue#392 <https://github.com/vantage6/vantage6/issues/392>`_,
   `PR#611 <https://github.com/vantage6/vantage6/pull/611>`_).
 - Share a node's database labels and types with the central server, so that the
   server can validate that these match between nodes and offer them as
   suggestions to the user when creating tasks
   (`Issue#750 <https://github.com/vantage6/vantage6/issues/750>`_,
   `PR#751 <https://github.com/vantage6/vantage6/pull/751>`_).
 - ``vnode new`` now automatically retrieves information on e.g. whether the
   collaboration is encrypted, so that the user doesn't have to specify this
   information themselves
   (`Issue#434 <https://github.com/vantage6/vantage6/issues/434>`_,
   `PR#739 <https://github.com/vantage6/vantage6/pull/739>`_).
 - Allow only unique names for organizations, collaborations, and nodes
   (`Issue#242 <https://github.com/vantage6/vantage6/issues/242>`_,
   `PR#515 <https://github.com/vantage6/vantage6/pull/515>`_).
 - New function ``client.task.wait_for_completion()`` for the `AlgorithmClient`
   to allow waiting for subtasks to complete
   (`Issue#651 <https://github.com/vantage6/vantage6/issues/651>`_,
   `PR#727 <https://github.com/vantage6/vantage6/pull/727>`_).
 - Improved validation of the input for all POST and PATCH requests using
   marshmallow schemas (`Issue#76 <https://github.com/vantage6/vantage6/issues/76>`_,
   `PR#744 <https://github.com/vantage6/vantage6/pull/744>`_).
 - Added option ``user_created`` to filter tasks that have been directly
   created by a user and are thus not subtasks
   (`Issue#583 <https://github.com/vantage6/vantage6/issues/583>`_,
   `PR#599 <https://github.com/vantage6/vantage6/pull/599>`_).
 - Users can now assign rules to other users that they don't have themselves
   if they do have higher permisions on the same resource
   (`Issue#443 <https://github.com/vantage6/vantage6/issues/443>`_,
   `PR#781 <https://github.com/vantage6/vantage6/pull/781>`_).

- **Change**

 - Changed the API response structure: no longer returning as many linked
   resources for performance reasons
   (`Issue#49 <https://github.com/vantage6/vantage6/issues/49>`_,
   `PR#709 <https://github.com/vantage6/vantage6/pull/709>`_)
 - The ``result`` endpoint has been renamed to ``run`` as this was a misnomer
   that concerns algorithm runs
   (`Issue#436 <https://github.com/vantage6/vantage6/issues/436>`_,
   `PR#527 <https://github.com/vantage6/vantage6/pull/527>`_),
   `PR#620 <https://github.com/vantage6/vantage6/pull/620>`_).
 - Split the `vantage6-client` package: the Python user client is kept in this
   package, and a new `vantage6-algorithm-tools` PyPI package is created for the
   tools that help algorithm developers. These tools were part of the client
   package, but moving them reduces the sizes of both packages
   (`Issue#662 <https://github.com/vantage6/vantage6/issues/662>`_,
   `PR#763 <https://github.com/vantage6/vantage6/pull/763>`_)
 - Removed environments `test`, `dev`, `prod`, `acc` and `application` from
   vantage6 servers and nodes as these were used little
   (`Issue#260 <https://github.com/vantage6/vantage6/issues/260>`_,
   `PR#643 <https://github.com/vantage6/vantage6/pull/643>`_)
 - Harmonized the interfaces between the `AlgorithmClient` and the `MockClient`
   (`Issue#669 <https://github.com/vantage6/vantage6/issues/669>`_,
   `PR#722 <https://github.com/vantage6/vantage6/pull/722>`_)
 - When users request resources where they are not allowed to see everything,
   they now get an unauthorized error instead of an incomplete or empty response
   (`Issue#635 <https://github.com/vantage6/vantage6/issues/635>`_,
   `PR#711 <https://github.com/vantage6/vantage6/pull/711>`_).
 - Node checks the server's version and by default, it pulls a matching image
   instead of the latest image of it's major version
   (`Issue#700 <https://github.com/vantage6/vantage6/issues/700>`_,
   `PR#706 <https://github.com/vantage6/vantage6/pull/706>`_).
 - ``vserver-local`` commands have been removed if they were not used within the
   docker images or the CLI (`Issue#663 <https://github.com/vantage6/vantage6/issues/663>`_,
   `PR#728 <https://github.com/vantage6/vantage6/pull/728>`_).
 - The way in which RabbitMQ is started locally has been changed to make it
   easier to run RabbitMQ locally. Now, a user indicates with a configuration
   flag whether they expect RabbitMQ to be started locally
   (`Issue#282 <https://github.com/vantage6/vantage6/issues/282>`_,
   `PR#795 <https://github.com/vantage6/vantage6/pull/795>`_).
 - The place in which server configuration files were stored on Linux has been
   changed fro ``/etc/xdg`` to ``/etc/vantage6/``
   (`Issue#269 <https://github.com/vantage6/vantage6/issues/269>`_,
   `PR#789 <https://github.com/vantage6/vantage6/pull/789>`_).
 - Backwards compatibility code that was present to make different v3.x versions
   compatible has been removed. Additionally, small improvements have been made
   that were not possible to do without breaking compatibility
   (`Issue#454 <https://github.com/vantage6/vantage6/issues/454>`_,
   `PR#740 <https://github.com/vantage6/vantage6/pull/740>`_,
   `PR#758 <https://github.com/vantage6/vantage6/pull/758>`_).

- **Bugfix**

 - Remove wrong dot in the version for prereleases  (
   `PR#764 <https://github.com/vantage6/vantage6/pull/764>`_).
 - Users were not assigned any permissions if `vserver import` was run before
   the server had ever been started
   (`Issue#634 <https://github.com/vantage6/vantage6/issues/634>`_,
   `PR#806 <https://github.com/vantage6/vantage6/pull/806>`_).

3.11.1
------

*11 September 2023*

- **Bugfix**

 - Setting up the host network for VPN did not work properly if the host had
   ``iptables-legacy`` installed rather than ``iptables``. Now, the code has
   been made compatible with both
   (`Issue#725 <https://github.com/vantage6/vantage6/issues/725>`_,
   `PR#802 <https://github.com/vantage6/vantage6/pull/802>`_).

3.11.0
------

*21 August 2023*

- **Feature**

 - A suite of `vdev` commands has been added to the CLI. These commands
   allow you to easily create a development environment for vantage6. The
   commands allow you to easily create a server configuration, add organizations
   and collaborations to it, and create the appropriate node configurations.
   Also, you can easily start, stop, and remove the network.
   (`Issue#625 <https://github.com/vantage6/vantage6/issues/625>`_,
   `PR#624 <https://github.com/vantage6/vantage6/pull/624>`_).
 - User Interface can now be started from the CLI with `vserver start --with-ui`
   (`Issue#730 <https://github.com/vantage6/vantage6/issues/730>`_,
   `PR#735 <https://github.com/vantage6/vantage6/pull/735>`_).
 - Added `created_at` and `finished_at` timestamps to tasks
   (`Issue#621 <https://github.com/vantage6/vantage6/issues/621>`_,
   `PR#715 <https://github.com/vantage6/vantage6/pull/715>`_).

- **Change**

 - Help text for the CLI has been updated and the formatting has been improved
   (`Issue#745 <https://github.com/vantage6/vantage6/issues/745>`_,
   `PR#791 <https://github.com/vantage6/vantage6/pull/791>`_).
 - With `vnode list`, the terms `online` and `offline` have been replaced by
   `running` and `not running`. This is more accurate, since a node may be
   unable to authenticate and thus be offline, but still be running.
   (`Issue#733 <https://github.com/vantage6/vantage6/issues/733>`_,
   `PR#734 <https://github.com/vantage6/vantage6/pull/734>`_).
 - Some legacy code that no longer fulfilled a function has been removed from
   the endpoint to create tasks
   (`Issue#742 <https://github.com/vantage6/vantage6/issues/742>`_,
   `PR#747 <https://github.com/vantage6/vantage6/pull/747>`_).

- **Bugfix**

 - In the docs, the example file to import server resources with
   `vserver import` was accidentally empty; now it contains example data.
   (`PR#792 <https://github.com/vantage6/vantage6/pull/792>`_).

3.10.4
------

*27 June 2023*

- **Change**

 - Extended the AlgorithmMockClient so that algorithm developers may pass it
   organization id's and node id's
   (`PR#737 <https://github.com/vantage6/vantage6/pull/737>`_).

- **Bugfix**

 - Speed up starting algorithm using VPN  (
   `Issue#681 <https://github.com/vantage6/vantage6/issues/681>`_,
   `PR#732 <https://github.com/vantage6/vantage6/pull/732>`_).
 - Updated VPN configurator Dockerfile so that VPN configuration works on
   Ubuntu 22 (`Issue#724 <https://github.com/vantage6/vantage6/issues/724>`_,
   `PR#725 <https://github.com/vantage6/vantage6/pull/725>`_).

3.10.3
------

*20 June 2023*

- **Bugfix**

 - Fixed bug in copying the MockClient itself to pass it on to a child task (
   `PR#723 <https://github.com/vantage6/vantage6/pull/723>`_).

.. note::

    Release 3.10.2 failed to be published to PyPI due to a gateway error,
    so that version was skipped.

3.10.1
------

*19 June 2023*

- **Bugfix**

 - Fixed bug in setting organization_id for the AlgorithmClient (
   `Issue#719 <https://github.com/vantage6/vantage6/issues/719>`_,
   `PR#720 <https://github.com/vantage6/vantage6/pull/720>`_).

3.10.0
------

*19 June 2023*

- **Feature**

 - There is a new implementation of a mock client, the ``MockAlgorithmClient``.
   This client is an improved version of the old ``ClientMockProtocol``. The
   new mock client now contains all the same functions as the regular client
   with the same signatures, and it returns the same data fields as those
   functions. Also, you may submit all supported data formats instead of just
   CSV files, and you may also submit pandas Dataframes directly
   (`Issue#683 <https://github.com/vantage6/vantage6/issues/683>`_,
   `PR#702 <https://github.com/vantage6/vantage6/pull/702>`_).

- **Change**

 - Updated cryptography dependency from 39.0.1 to 41.0.0
   (`PR#707 <https://github.com/vantage6/vantage6/pull/707>`_,
   `PR#708 <https://github.com/vantage6/vantage6/pull/708>`_).

- **Bugfix**

 - A node's VPN IP address was previously only updated when a new task was
   started on that node. Instead, it is now updated properly on VPN connect/
   disconnect (`Issue#520 <https://github.com/vantage6/vantage6/issues/520>`_,
   `PR#704 <https://github.com/vantage6/vantage6/pull/704>`_).

3.9.0
-----

*25 May 2023*

- **Feature**

 - Data sources may now be whitelisted by IP address, so that an
   algorithm may access those IP addresses to obtain data. This is achieved
   via a Squid proxy server
   (`Issue#162 <https://github.com/vantage6/vantage6/issues/162>`_,
   `PR#626 <https://github.com/vantage6/vantage6/pull/626>`_).
 - There is a new configuration option to let algorithms access gpu's
   (`Issue#597 <https://github.com/vantage6/vantage6/issues/597>`_,
   `PR#623 <https://github.com/vantage6/vantage6/pull/623>`_).
 - Added option to get VPN IP addresses and ports of just the children or
   just the parent of an algorithm that is running. These options may be used
   to simplify VPN communication between algorithms running on different nodes.
   In the AlgorithmClient, the functions ``client.vpn.get_child_addresses()``
   and ``client.vpn.get_parent_address()`` have been added
   (`PR#610 <https://github.com/vantage6/vantage6/pull/610>`_).
 - New option to print the full stack trace of algorithm errors. Note that
   this option may leak sensitive information if used carelessly. The option
   may be activated by setting ``log_traceback=True`` in the algorithm wrapper
   (`Issue#675 <https://github.com/vantage6/vantage6/issues/675>`_,
   `PR#680 <https://github.com/vantage6/vantage6/pull/680>`_).
 - Configuration options to control the log levels of individual dependencies.
   This allows easier debugging when a certain dependency is causing issues
   (`Issue#641 <https://github.com/vantage6/vantage6/issues/641>`_,
   `PR#642 <https://github.com/vantage6/vantage6/pull/642>`_).

- **Change**

 - Better error message for ``vnode attach`` when no nodes are running
   (`Issue#606 <https://github.com/vantage6/vantage6/issues/606>`_,
   `PR#607 <https://github.com/vantage6/vantage6/pull/607>`_).
 - The number of characters of the task input printed to the logs is now limited
   to prevent flooding the logs with very long input
   (`Issue#549 <https://github.com/vantage6/vantage6/issues/549>`_,
   `PR#550 <https://github.com/vantage6/vantage6/pull/550>`_).
 - Node proxy logs are now written to a separate log file. This makes the
   main node log more readable
   (`Issue#546 <https://github.com/vantage6/vantage6/issues/546>`_,
   `PR#619 <https://github.com/vantage6/vantage6/pull/619>`_).
 - Update code in which the version is updated
   (`PR#586 <https://github.com/vantage6/vantage6/pull/586>`_).
 - Finished standardizing docstrings - note that this was already partially
   done in earlier releases
   (`Issue#255 <https://github.com/vantage6/vantage6/issues/255>`_).
 - Cleanup and moving of unused code and duplicate code
   (`PR#571 <https://github.com/vantage6/vantage6/pull/571>`_).
 - It is now supported to run the release pipeline from ``release/v<x.y.z>``
   branches (`Issue#467 <https://github.com/vantage6/vantage6/issues/467>`_,
   `PR#488 <https://github.com/vantage6/vantage6/pull/488>`_).
 - Replaced deprecated ``set-output`` method in Github actions release pipeline
   (`Issue#474 <https://github.com/vantage6/vantage6/issues/474>`_,
   `PR#601 <https://github.com/vantage6/vantage6/pull/601>`_).

- **Bugfix**

 - Fixed checking for newer images (node, server, and algorithms). Previously,
   the dates used were not sufficient to check if an image was newer. Now,
   we are also checking the image digest
   (`Issue#507 <https://github.com/vantage6/vantage6/issues/507>`_,
   `PR#602 <https://github.com/vantage6/vantage6/pull/602>`_).
 - Users are prevented from posting socket events that are meant for nodes -
   note that nothing harmful could be done but it should not be possible
   nevertheless (`Issue#615 <https://github.com/vantage6/vantage6/issues/615>`_,
   `PR#616 <https://github.com/vantage6/vantage6/pull/616>`_).
 - Fixed bug with detecting if database was a file as '/mnt/' was not properly
   prepended to the file path
   (`PR#691 <https://github.com/vantage6/vantage6/pull/691>`_).

3.8.8
-----

*11 May 2023*

- **Bugfix**

   - Fixed a bug that prevented the node from shutting down properly
     (`Issue#649 <https://github.com/vantage6/vantage6/issues/649>`_,
     `PR#677 <https://github.com/vantage6/vantage6/pull/677>`_)
   - Fixed a bug where the node did not await the VPN client to be ready
     (`Issue#656 <https://github.com/vantage6/vantage6/issues/656>`_,
     `PR#676 <https://github.com/vantage6/vantage6/pull/676>`_)
   - Fixed database label logging
     (`PR#664 <https://github.com/vantage6/vantage6/pull/664>`_)
   - Fixed a bug were VPN messages to the originating node where not always
     sent/received
     (`Issue#671 <https://github.com/vantage6/vantage6/issues/671>`_,
     `PR#673 <https://github.com/vantage6/vantage6/pull/673>`_)
   - Fixed a bug where an exceptions is raised when the websocket
     connection was lost and a ping was attempted to be send
     (`Issue#672 <https://github.com/vantage6/vantage6/issues/672>`_,
     `PR#674 <https://github.com/vantage6/vantage6/pull/674>`_)
   - Fixed a formatting in CLI print statement
     (`PR#661 <https://github.com/vantage6/vantage6/pull/661>`_)
   - Fixed bug where '/mnt/' was erroneously prepended to non-file based
     databases (`PR#658 <https://github.com/vantage6/vantage6/pull/658>`_)
   - Fix in ``autowrapper`` for algorithms with CSV input
     (`PR#655 <https://github.com/vantage6/vantage6/pull/655>`_)
   - Fixed a bug in syncing tasks from the server to the node, when the node
     lost socket connection and then reconnected
     (`Issue#654 <https://github.com/vantage6/vantage6/issues/654>`_,
     `PR#657 <https://github.com/vantage6/vantage6/pull/657>`_)
   - Fix construction of database URI in ``vserver files``
     (`Issue#650 <https://github.com/vantage6/vantage6/issues/650>`_,
     `PR#659 <https://github.com/vantage6/vantage6/pull/659>`_)


3.8.7
-----

*10 May 2023*

- **Bugfix**

   - Socket did connect before Docker was initialized, resulting in an exception
     at startup (`PR#644 <https://github.com/vantage6/vantage6/pull/644>`_)

3.8.6
-----

*9 May 2023*

- **Bugfix**

   - Fixed bug that resulted in broken algorithm networks when the socket
     connection was lost (`PR#640 <https://github.com/vantage6/vantage6/pull/640>`_,
     `Issue#637 <https://github.com/vantage6/vantage6/issues/637>`_)

3.8.3 - 3.8.5
-------------

*25 April 2023 - 2 May 2023*

- **Bugfix**

 - Fixed bug where a missing container lead to a complete node crash
   (`PR#628  <https://github.com/vantage6/vantage6/pull/628>`_,
   `PR#629 <https://github.com/vantage6/vantage6/pull/629>`_,
   `PR#632 <https://github.com/vantage6/vantage6/pull/632>`_).
 - Restored algorithm wrapper namespace for backward compatibility (
   `PR#618 <https://github.com/vantage6/vantage6/pull/618>`_)
 - Prevent error with first socket ping on node startup by waiting a few
   seconds (`PR#609 <https://github.com/vantage6/vantage6/pull/609>`_)

3.8.2
-----

*22 march 2023*


- **Feature**

 - Location of the server configuration file in server shell script can now be
   specified as an environment variable (`PR#604 <https://github.com/vantage6/vantage6/pull/604>`_)

- **Change**

 - Changed ping/pong mechanism over socket connection between server and nodes,
   as it did not function properly in combination with RabbitMQ. Now, the node
   pushes a ping and the server periodically checks if the node is still alive
   (`PR#593 <https://github.com/vantage6/vantage6/pull/593>`_)

- **Bugfix**

 - For ``vnode files``, take the new formatting of the databases in the node
   configuration file into account (`PR#600 <https://github.com/vantage6/vantage6/pull/600>`_)
 - Fix bugs in new algorithm client where class attributes were improperly
   referred to (`PR#596 <https://github.com/vantage6/vantage6/pull/596>`_)
 - Fixed broken links in Discord notification
   (`PR#591 <https://github.com/vantage6/vantage6/pull/591>`_)

3.8.1
-----

*8 march 2023*

- **Bugfix**

 - In 3.8.0, starting RabbitMQ for horizontal scaling caused a server crash
   due to a missing ``kombu`` dependency. This dependency was wrongly removed
   in updating all dependencies for python 3.10 (
   `PR#585 <https://github.com/vantage6/vantage6/pull/585>`_).

3.8.0
-----

*8 march 2023*

- **Security**

 - Refresh tokens are no longer indefinitely valid (
   `CVE#CVE-2023-23929 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-23929>`_,
   `commit <https://github.com/vantage6/vantage6/commit/48ebfca42359e9a6743e9598684585e2522cdce8>`__).
 - It was possible to obtain usernames by brute forcing the login since v3.3.0.
   This was due to a change where users got to see a message their account was
   blocked after N failed login attempts. Now, users get an email instead if
   their account is blocked (
   `CVE#CVE-2022-39228 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-39228>`_,
   `commit <https://github.com/vantage6/vantage6/commit/ab4381c35d24add06f75d5a8a284321f7a340bd2>`__
   ).
 - Assigning existing users to a different organizations was possible. This may
   lead to unintended access: if a user from organization A is accidentally
   assigned to organization B, they will retain their permissions and
   therefore might be able to access resources they should not be allowed to
   access (`CVE#CVE-2023-22738 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-22738>`_,
   `commit <https://github.com/vantage6/vantage6/commit/798aca1de142a4eca175ef51112e2235642f4f24>`__).

- **Feature**

 - Python version upgrade to 3.10 and many dependencies are upgraded (
   `PR#513 <https://github.com/vantage6/vantage6/pull/513>`_,
   `Issue#251 <https://github.com/vantage6/vantage6/issues/251>`_).
 - Added ``AlgorithmClient`` which will replace ``ContainerClient`` in v4.0.
   For now, the new ``AlgorithmClient`` can be used by specifying
   ``use_new_client=True`` in the algorithm wrapper (
   `PR#510 <https://github.com/vantage6/vantage6/pull/510>`_,
   `Issue#493 <https://github.com/vantage6/vantage6/issues/493>`_).
 - It is now possible to request some of the node configuration settings, e.g.
   which algorithms they allow to be run (
   `PR#523 <https://github.com/vantage6/vantage6/pull/523>`_,
   `Issue#12 <https://github.com/vantage6/vantage6/issues/12>`_).
 - Added ``auto_wrapper`` which detects the data source types and reads the
   data accordingly. This removes the need to rebuild every algorithm for
   every data source type (
   `PR#555 <https://github.com/vantage6/vantage6/pull/555>`_,
   `Issue#553 <https://github.com/vantage6/vantage6/issues/553>`_).
 - New endpoint added ``/vpn/algorithm/addresses`` for algorithms to obtain
   addresses for containers that are part of the same computation task (
   `PR#501 <https://github.com/vantage6/vantage6/pull/501>`_,
   `Issue#499 <https://github.com/vantage6/vantage6/issues/499>`_).
 - Added the option to allow only allow certain organization and/or users
   to run tasks on your node. This can be done by using the ``policies``
   configuration option. Note that the ``allowed_images`` option is now
   nested under the ``policies`` option (
   `Issue#335 <https://github.com/vantage6/vantage6/issues/335>`_,
   `PR#556 <https://github.com/vantage6/vantage6/pull/556>`_)

- **Change**

 - Some changes have been made to the release pipeline (
   `PR#519 <https://github.com/vantage6/vantage6/pull/519>`_,
   `PR#488 <https://github.com/vantage6/vantage6/pull/488>`_,
   `PR#500 <https://github.com/vantage6/vantage6/pull/500>`_,
   `Issue#485 <https://github.com/vantage6/vantage6/issues/485>`_).
 - Removed unused script to start the shell (
   `PR#494 <https://github.com/vantage6/vantage6/pull/494>`_).

- **Bugfix**

 - Algorithm containers running on the same node could not communicate with
   each other through the VPN. This has been fixed (
   `PR#532 <https://github.com/vantage6/vantage6/pull/532>`_,
   `Issue#336 <https://github.com/vantage6/vantage6/issues/336>`_).


3.7.3
-----

*22 february 2023*

- **Bugfix**

 -  A database commit in 3.7.2 was done on the wrong variable, this has been
    corrected (`PR#547 <https://github.com/vantage6/vantage6/pull/547>`_,
    `Issue#534 <https://github.com/vantage6/vantage6/issues/534>`_).
 -  Delete entries in the VPN port table after the algorithm has completed
    (`PR#548 <https://github.com/vantage6/vantage6/pull/548>`_).
 -  Limit number of characters of the task input printed to the logs
    (`PR#550 <https://github.com/vantage6/vantage6/pull/550>`_).

3.7.2
-----

*20 february 2023*

- **Bugfix**

 -  In 3.7.1, some sessions were closed, but not all. Now, sessions are also
    terminated in the socketIO events
    (`PR#543 <https://github.com/vantage6/vantage6/pull/543>`_,
    `Issue#534 <https://github.com/vantage6/vantage6/issues/534>`_).
 -  Latest versions of VPN images were not automatically downloaded by node
    on VPN connection startup. This has been corrected (
    `PR#542 <https://github.com/vantage6/vantage6/pull/542>`_).

3.7.1
-----

*16 february 2023*

- **Change**

 -  Some changes to the release pipeline.

- **Bugfix**

 -  ``iptables`` dependency was missing in the VPN client container (
    `PR#533 <https://github.com/vantage6/vantage6/pull/533>`_
    `Issue#518 <https://github.com/vantage6/vantage6/issues/518>`_).
 -  Fixed a bug that did not close Postgres DB sessions, resulting in a dead
    server (`PR#540 <https://github.com/vantage6/vantage6/pull/540>`_,
    `Issue#534 <https://github.com/vantage6/vantage6/issues/534>`_).


3.7.0
-----

*25 january 2023*

- **Feature**

 -  SSH tunnels are available on the node. This allows nodes to connect to
    other machines over SSH, thereby greatly expanding the options to connect
    databases and other services to the node, which before could only be made
    available to the algorithms if they were running on the same machine as the
    node (`PR#461 <https://github.com/vantage6/vantage6/pull/461>`__,
    `Issue#162 <https://github.com/vantage6/vantage6/issues/162>`__).
 -  For two-factor authentication, the information given to the authenticator
    app has been updated to include a clearer description of the server and
    username (`PR#483 <https://github.com/vantage6/vantage6/pull/483>`__,
    `Issue#405 <https://github.com/vantage6/vantage6/issues/405>`__).
 -  Added the option to run an algorithm without passing data to it using the
    CSV wrapper (`PR#465 <https://github.com/vantage6/vantage6/pull/465>`__)
 -  In the UI, when users are about to create a task, they will now be shown
    which nodes relevant to the task are offline
    (`PR#97 <https://github.com/vantage6/vantage6-UI/pull/97>`__,
    `Issue#96 <https://github.com/vantage6/vantage6-UI/issues/96>`__).

- **Change**

 -  The ``docker`` dependency is updated, so that ``docker.pull()`` now pulls
    the `default` tag if no tag is specified, instead of all tags
    (`PR#481 <https://github.com/vantage6/vantage6/pull/481>`__,
    `Issue#473 <https://github.com/vantage6/vantage6/issues/473>`__).
 -  If a node cannot authenticate to the server because the server cannot be
    found, the user now gets a clearer error message(`PR#480 <https://github.com/vantage6/vantage6/pull/480>`__,
    `Issue#460 <https://github.com/vantage6/vantage6/issues/460>`__).
 -  The default role 'Organization admin' has been updated: it now allows to
    create nodes for their own organization
    (`PR#489 <https://github.com/vantage6/vantage6/pull/489>`__).
 -  The release pipeline has been updated to 1) release to PyPi as last step (
    since that is irreversible), 2) create release branches, 3) improve the
    check on the version tag, and 4) update some soon-to-be-deprecated commands
    (`PR#488 <https://github.com/vantage6/vantage6/pull/488>`__.
 -  Not all nodes are alerted any more when a node comes online
    (`PR#490 <https://github.com/vantage6/vantage6/pull/490>`__).
 -  Added instructions to the UI on how to report bugs
    (`PR#100 <https://github.com/vantage6/vantage6-UI/pull/100>`__,
    `Issue#57 <https://github.com/vantage6/vantage6-UI/issues/57>`__).


- **Bugfix**

 -  Newer images were not automatically pulled from harbor on node or server
    startup. This has been fixed (`PR#482 <https://github.com/vantage6/vantage6/pull/482>`__,
    `Issue#471 <https://github.com/vantage6/vantage6/issues/471>`__).

3.6.1
-----

*12 january 2023*

- **Feature**

 -  Algorithm containers can be killed from the client. This can be done
    for a specific task or it possible to kill all tasks running at a specific
    node (`PR#417 <https://github.com/vantage6/vantage6/pull/417>`__,
    `Issue#167 <https://github.com/vantage6/vantage6/issues/167>`__).
 -  Added a ``status`` field for an algorithm, that tracks if an algorithm has
    yet to start, is started, has finished, or has failed. In the latter case,
    it also indicates how/when the algorithm failed
    (`PR#417 <https://github.com/vantage6/vantage6/pull/417>`__).
 -  The UI has been connected to the socket, and gives messages about node
    and task status changes (`UI PR#84 <https://github.com/vantage6/vantage6-UI/pull/84>`_,
    `UI Issue #73 <https://github.com/vantage6/vantage6-UI/issues/73>`_). There
    are also new permissions for socket events on the server to authorize users
    to see events from their (or all) collaborations
    (`PR#417 <https://github.com/vantage6/vantage6/pull/417>`_).
 -  It is now possible to create tasks in the UI (UI version >3.6.0). Note that
    all tasks are then JSON serialized and you will not be able to run tasks
    in an encrypted collaboration (as that would require uploading a private
    key to a browser) (`PR#90 <#https://github.com/vantage6/vantage6-UI/pull/90>`_).

    .. warning::
        If you want to run the UI Docker image, note that from this version
        onwards, you have to define the ``SERVER_URL`` and ``API_PATH``
        environment variables (compared to just a ``API_URL`` before).
 -  There is a new multi-database wrapper that will forward a dictionary of all
    node databases and their paths to the algorithm. This allows you to use
    multiple databases in a single algorithm easily.
    (`PR#424 <https://github.com/vantage6/vantage6/pull/424>`_,
    `Issue #398 <https://github.com/vantage6/vantage6/issues/398>`_).
 -  New rules are now assigned automatically to the default root role. This
    ensures that rules that are added in a new version are assigned to system
    administrators, instead of them having to change the database
    (`PR#456 <https://github.com/vantage6/vantage6/pull/456>`_,
    `Issue #442 <https://github.com/vantage6/vantage6/issues/442>`_).
 -  There is a new command ``vnode set-api-key`` that facilitates putting your
    API key into the node configuration file (`PR#428 <https://github.com/vantage6/vantage6/pull/418>`_,
    `Issue #259 <https://github.com/vantage6/vantage6/issues/259>`_).
 -  Logging in the Python client has been improved: instead of all or nothing,
    log level is now settable to one of debug, info, warn, error, critical
    (`PR#453 <https://github.com/vantage6/vantage6/pull/453>`_,
    `Issue #340 <https://github.com/vantage6/vantage6/issues/340>`_).
 -  When there is an error in the VPN server configuration, the user receives
    clearer error messages than before (`PR#444 <https://github.com/vantage6/vantage6/pull/444>`_,
    `Issue #278 <https://github.com/vantage6/vantage6/issues/278>`_).

- **Change**

 -  The node status (online/offline) is now checked periodically over the socket
    connection via a ping/pong construction. This is an improvement over the
    older version where a node's status was changed only when it connected or
    disconnected (`PR#450 <https://github.com/vantage6/vantage6/pull/450>`_,
    `Issue #40 <https://github.com/vantage6/vantage6/issues/40>`_).

    .. warning::
        If a server upgrades to 3.6.1, the nodes should also be upgraded.
        Otherwise, the node status will be incorrect and the logs will show
        errors periodically with each attempted ping/pong.
 -  It is no longer possible for any user to change the username of another
    user, as this would be confusing for that user when logging in
    (`PR#433 <https://github.com/vantage6/vantage6/pull/433>`_,
    `Issue #396 <https://github.com/vantage6/vantage6/issues/396>`_).
 -  The server has shorter log messages when someone calls a non-existing route.
    The resulting 404 exception is no longer logged (`PR#452 <https://github.com/vantage6/vantage6/pull/452>`_,
    `Issue #393 <https://github.com/vantage6/vantage6/issues/393>`_).
 -  Removed old, unused scripts to start a node
    (`PR#464 <https://github.com/vantage6/vantage6/pull/464>`_).

- **Bugfix**

 -  Node was unable to pull images from Docker Hub; this has been corrected.
    (`PR#432 <https://github.com/vantage6/vantage6/pull/432>`__,
    `Issue#422 <https://github.com/vantage6/vantage6/issues/422>`__).
 -  File-based database extensions were always converted to ``.csv`` when they
    were mounted to a node. Now, files keep their original file extensions
    (`PR#426 <https://github.com/vantage6/vantage6/pull/426>`_,
    `Issue #397 <https://github.com/vantage6/vantage6/issues/397>`_).
 -  When a node configuration defined a wrong VPN subnet, the VPN connection
    didn't work but this was not detected until VPN was used. Now, the user is
    alerted immediately and VPN is turned off
    (`PR#444 <https://github.com/vantage6/vantage6/pull/444>`_).
 -  If a user tries to write a node or server config file to a non-existing
    directory, they are now getting a clear error message instead of an
    incorrect one (`PR#455 <https://github.com/vantage6/vantage6/pull/455>`_,
    `Issue #1 <https://github.com/vantage6/vantage6/issues/1>`_)
 -  There was a circular import in the infrastructure code, which has now been
    resolved (`PR#451 <https://github.com/vantage6/vantage6/pull/451>`_,
    `Issue #53 <https://github.com/vantage6/vantage6/issues/53>`_).
 -  In PATCH ``/user``, it was not possible to set some fields (e.g.
    ``firstname``) to an empty string if there was a value before.
    (`PR#439 <https://github.com/vantage6/vantage6/pull/439>`_,
    `Issue #334 <https://github.com/vantage6/vantage6/issues/334>`_).


.. note::
    Release 3.6.0 was skipped due to an issue in the release process.

3.5.2
-----

*30 november 2022*

-  **Bugfix**

  -  Fix for automatic addition of column. This failed in some SQL
     dialects because reserved keywords (i.e. 'user' for PostgresQL) were
     not escaped
     (`PR#415 <https://github.com/vantage6/vantage6/pull/415>`__)
  -  Correct installation order for uWSGI in node and server docker file
     (`PR#414 <https://github.com/vantage6/vantage6/pull/414>`__)

.. _section-1:

3.5.1
-----

*30 november 2022*

-  **Bugfix**

 -  Backwards compatibility for which organization initiated a task
    between v3.0-3.4 and v3.5
    (`PR#412 <https://github.com/vantage6/vantage6/pull/413>`__)
 -  Fixed VPN client container. Entry script was not executable in Github
    pipelines
    (`PR#413 <https://github.com/vantage6/vantage6/pull/413>`__)

3.5.0
-----

*30 november 2022*

.. warning::
   When upgrading to 3.5.0, you might need to add the **otp_secret** column to
   the **user** table manually in the database. This may be avoided by upgrading
   to 3.5.2.

-  **Feature**

  -  Multi-factor authentication via TOTP has been added. Admins can enforce
     that all users enable MFA
     (`PR#376 <https://github.com/vantage6/vantage6/pull/376>`__,
     `Issue#355 <https://github.com/vantage6/vantage6/issues/355>`__).
  -  You can now request all tasks assigned by a given user
     (`PR#326 <https://github.com/vantage6/vantage6/pull/326>`__,
     `Issue#43 <https://github.com/vantage6/vantage6/issues/43>`__).
  -  The server support email is now settable in the configuration
     file, used to be fixed at ``support@vantage6.ai``
     (`PR#330 <https://github.com/vantage6/vantage6/pull/330>`__,
     `Issue#319 <https://github.com/vantage6/vantage6/issues/319>`__).
  -  When pickles are used, more task info is shown in the node logs
     (`PR#366 <https://github.com/vantage6/vantage6/pull/366>`__,
     `Issue#171 <https://github.com/vantage6/vantage6/issues/171>`__).

-  **Change**

  -  The ``harbor2.vantag6.ai/infrastructure/algorithm-base:[TAG]`` is
     tagged with the vantage6-client version that is already in the
     image (`PR#389 <https://github.com/vantage6/vantage6/pull/389>`__,
     `Issue#233 <https://github.com/vantage6/vantage6/issues/233>`__).
  -  The infrastructure base image has been updated to improve build
     time (`PR#406 <https://github.com/vantage6/vantage6/pull/406>`__,
     `Issue#250 <https://github.com/vantage6/vantage6/issues/250>`__).


3.4.2
-----

*3 november 2022*

-  **Bugfix**

  -  Fixed a bug in the local proxy server which made algorithm containers crash
     in case the `client.create_new_task` method was used
     (`PR#382 <https://github.com/vantage6/vantage6/pull/382>`_).
  -  Fixed a bug where the node crashed when a non existing image was sent in a
     task (`PR#375 <https://github.com/vantage6/vantage6/pull/375>`_).


3.4.0 & 3.4.1
-------------

*25 oktober 2022*

-  **Feature**

  -  Add columns to the SQL database on startup
     (`PR#365 <https://github.com/vantage6/vantage6/pull/365>`__,
     `ISSUE#364 <https://github.com/vantage6/vantage6/issues/364>`__).
     This simpifies the upgrading proces when a new column is added in
     the new release, as you do no longer need to manually add columns.
     When downgrading the columns will **not** be deleted.
  -  Docker wrapper for Parquet files
     (`PR#361 <https://github.com/vantage6/vantage6/pull/361>`__,
     `ISSUE#337 <https://github.com/vantage6/vantage6/issues/337>`__).
     Parquet provides a way to store tabular data with the datatypes
     included which is an advantage over CSV.
  -  When the node starts, or when the client is verbose initialized a
     banner to cite the vantage6 project is added
     (`PR#359 <https://github.com/vantage6/vantage6/pull/359>`__,
     `ISSUE#356 <https://github.com/vantage6/vantage6/issues/356>`__).
  -  In the client a waiting for results method is added
     (`PR#325 <https://github.com/vantage6/vantage6/pull/325>`__,
     `ISSUE#8 <https://github.com/vantage6/vantage6/issues/8>`__).
     Which allows you to automatically poll for results by using
     ``client.wait_for_results(...)``, for more info see
     ``help(client.wait_for_results)``.
  -  Added Github releases
     (`PR#358 <https://github.com/vantage6/vantage6/pull/358>`__,
     `ISSUE#357 <https://github.com/vantage6/vantage6/issues/357>`__).
  -  Added option to filter GET ``/role`` by user id in the Python client
     (`PR#328 <https://github.com/vantage6/vantage6/pull/328>`__,
     `ISSUE#213 <https://github.com/vantage6/vantage6/issues/213>`__).
     E.g.: ``client.role.list(user=...).``
  - In release process, build and release images for both ARM and x86
    architecture.

-  **Change**

  -  Unused code removed from the Makefile
     (`PR#324 <https://github.com/vantage6/vantage6/issues/357>`__,
     `ISSUE#284 <https://github.com/vantage6/vantage6/issues/284>`__).
  -  Pandas version is frozen to version 1.3.5
     (`PR#363 <https://github.com/vantage6/vantage6/pull/363>`__ ,
     `ISSUE#266 <https://github.com/vantage6/vantage6/issues/266>`__).

-  **Bugfix**

  -  Improve checks for non-existing resources in unittests
     (`PR#320 <https://github.com/vantage6/vantage6/pull/320>`__,
     `ISSUE#265 <https://github.com/vantage6/vantage6/issues/265>`__).
     Flask did not support negative ints, so the tests passed due to
     another 404 response.
  -  ``client.node.list`` does no longer filter by offline nodes
     (`PR#321 <https://github.com/vantage6/vantage6/pull/321>`__,
     `ISSUE#279 <https://github.com/vantage6/vantage6/issues/279>`__).

.. note::
   3.4.1 is a rebuild from 3.4.0 in which the all dependencies are fixed, as
   the build led to a broken server image.

3.3.7
-----

-  **Bugfix**

  -  The function ``client.util.change_my_password()`` was updated
     (`Issue #333 <https://github.com/vantage6/vantage6/issues/333>`__)

3.3.6
-----

-  **Bugfix**

  -  Temporary fix for a bug that prevents the master container from
     creating tasks in an encrypted collaboration. This temporary fix
     disables the parallel encryption module in the local proxy. This
     functionality will be restored in a future release.

.. note::
    This version is also the first version where the User Interface is available
    in the right version. From this point onwards, the user interface changes
    will also be part of the release notes.

3.3.5
-----

-  **Feature**

  -  The release pipeline has been expanded to automatically push new
     Docker images of node/server to the harbor2 service.

-  **Bugfix**

  -  The VPN IP address for a node was not saved by the server using
     the PATCH ``/node`` endpoint, while this functionality is required
     to use the VPN

.. note::
    Note that 3.3.4 was only released on PyPi and that version is identical
    to 3.3.5. That version was otherwise skipped due to a temporary mistake
    in the release pipeline.

3.3.3
-----

-  **Bugfix**

  -  Token refresh was broken for both users and nodes.
     (`Issue#306 <https://github.com/vantage6/vantage6/issues/306>`__,
     `PR#307 <https://github.com/vantage6/vantage6/pull/307>`__)
  -  Local proxy encrpytion was broken. This prefented algorithms from
     creating sub tasks when encryption was enabled.
     (`Issue#305 <https://github.com/vantage6/vantage6/issues/305>`__,
     `PR#308 <https://github.com/vantage6/vantage6/pull/308>`__)

3.3.2
-----

-  **Bugfix**

  -  ``vpn_client_image`` and ``network_config_image`` are settable
     through the node configuration file.
     (`PR#301 <https://github.com/vantage6/vantage6/pull/301>`__,
     `Issue#294 <https://github.com/vantage6/vantage6/issues/294>`__)
  -  The option ``--all`` from ``vnode stop`` did not stop the node
     gracefully. This has been fixed. It is possible to force the nodes
     to quit by using the ``--force`` flag.
     (`PR#300 <https://github.com/vantage6/vantage6/pull/300>`__,
     `Issue#298 <https://github.com/vantage6/vantage6/issues/298>`__)
  -  Nodes using a slow internet connection (high ping) had issues with
     connecting to the websocket channel.
     (`PR#299 <https://github.com/vantage6/vantage6/pull/299>`__,
     `Issue#297 <https://github.com/vantage6/vantage6/issues/297>`__)

3.3.1
-----

-  **Bugfix**

  -  Fixed faulty error status codes from the ``/collaboration``
     endpoint
     (`PR#287 <https://github.com/vantage6/vantage6/pull/287>`__).
  -  *Default* roles are always returned from the ``/role`` endpoint.
     This fixes the error when a user was assigned a *default* role but
     could not reach anything (as it could not view its own role)
     (`PR#286 <https://github.com/vantage6/vantage6/pull/286>`__).
  -  Performance upgrade in the ``/organization`` endpoint. This caused
     long delays when retrieving organization information when the
     organization has many tasks
     (`PR#288 <https://github.com/vantage6/vantage6/pull/288>`__).
  -  Organization admins are no longer allowed to create and delete
     nodes as these should be managed at collaboration level.
     Therefore, the collaboration admin rules have been extended to
     include create and delete nodes rules
     (`PR#289 <https://github.com/vantage6/vantage6/pull/289>`__).
  -  Fixed some issues that made ``3.3.0`` incompatible with ``3.3.1``
     (`Issue#285 <https://github.com/vantage6/vantage6/issues/285>`__).

3.3.0
-----

-  **Feature**

  -  Login requirements have been updated. Passwords are now required
     to have sufficient complexity (8+ characters, and at least 1
     uppercase, 1 lowercase, 1 digit, 1 special character). Also, after
     5 failed login attempts, a user account is blocked for 15 minutes
     (these defaults can be changed in a server config file).
  -  Added endpoint ``/password/change`` to allow users to change their
     password using their current password as authentication. It is no
     longer possible to change passwords via ``client.user.update()``
     or via a PATCH ``/user/{id}`` request.
  -  Added the default roles ‘viewer’, ‘researcher’, ‘organization
     admin’ and ‘collaboration admin’ to newly created servers. These
     roles may be assigned to users of any organization, and should
     help users with proper permission assignment.
  -  Added option to filter get all roles for a specific user id in the
     GET ``/role`` endpoint.
  -  RabbitMQ has support for multiple servers when using
     ``vserver start``. It already had support for multiple servers
     when deploying via a Docker compose file.
  -  When exiting server logs or node logs with Ctrl+C, there is now an
     additional message alerting the user that the server/node is still
     running in the background and how they may stop them.

-  **Change**

  -  Node proxy server has been updated
  -  Updated PyJWT and related dependencies for improved JWT security.
  -  When nodes are trying to use a wrong API key to authenticate, they
     now receive a clear message in the node logs and the node exits
     immediately.
  -  When using ``vserver import``, API keys must now be provided for
     the nodes you create.
  -  Moved all swagger API docs from YAML files into the code. Also,
     corrected errors in them.
  -  API keys are created with UUID4 instead of UUID1. This prevents
     that UUIDs created milliseconds apart are not too similar.
  -  Rules for users to edit tasks were never used and have therefore
     been deleted.

-  **Bugfix**

  -  In the Python client, ``client.organization.list()`` now shows
     pagination metadata by default, which is consistent all other
     ``list()`` statements.
  -  When not providing an API key in ``vnode new``, there used to be
     an unclear error message. Now, we allow specifying an API key
     later and provide a clearer error message for any other keys with
     inadequate values.
  -  It is now possible to provide a name when creating a name, both
     via the Python client as via the server.
  -  A GET ``/role`` request crashed if parameter ``organization_id``
     was defined but not ``include_root``. This has been resolved.
  -  Users received an ‘unexpected error’ when performing a GET
     ``/collaboration?organization_id=<id>`` request and they didn’t
     have global collaboration view permission. This was fixed.
  -  GET ``/role/<id>`` didn’t give an error if a role didn’t exist.
     Now it does.

3.2.0
-----

-  **Feature**

  -  Horizontal scaling for the vantage6-server instance by adding
     support for RabbitMQ.
  -  It is now possible to connect other docker containers to the
     private algorithm network. This enables you to attach services to
     the algorithm network using the ``docker_services`` setting.
  -  Many additional select and filter options on API endpoints, see
     swagger docs endpoint (``/apidocs``). The new options have also
     been added to the Python client.
  -  Users are now always able to view their own data
  -  Usernames can be changed though the API

-  **Bugfix**

  -  (Confusing) SQL errors are no longer returned from the API.
  -  Clearer error message when an organization has multiple nodes for
     a single collaboration.
  -  Node no longer tries to connect to the VPN if it has no
     ``vpn_subnet`` setting in its configuration file.
  -  Fix the VPN configuration file renewal
  -  Superusers are no longer able to post tasks to collaborations its
     organization does not participate in. Note that superusers were
     never able to view the results of such tasks.
  -  It is no longer possible to post tasks to organization which do
     not have a registered node attach to the collaboration.
  -  The ``vnode create-private-key`` command no longer crashes if the
     ssh directory does not exist.
  -  The client no longer logs the password
  -  The version of the ``alpine`` docker image (that is used to set up
     algorithm runs with VPN) was fixed. This prevents that many
     versions of this image are downloaded by the node.
  -  Improved reading of username and password from docker registry,
     which can be capitalized differently depending on the docker
     version.
  -  Fix error with multiple-database feature, where default is now
     used if specific database is not found

3.1.0
-----

-  **Feature**

  -  Algorithm-to-algorithm communication can now take place over
     multiple ports, which the algorithm developer can specify in the
     Dockerfile. Labels can be assigned to each port, facilitating
     communication over multiple channels.
  -  Multi-database support for nodes. It is now also possible to
     assign multiple data sources to a single node in Petronas; this
     was already available in Harukas 2.2.0. The user can request a
     specific data source by supplying the *database* argument when
     creating a task.
  -  The CLI commands ``vserver new`` and ``vnode new`` have been
     extended to facilitate configuration of the VPN server.
  -  Filter options for the client have been extended.
  -  Roles can no longer be used across organizations (except for roles
     in the default organization)
  -  Added ``vnode remove`` command to uninstall a node. The command
     removes the resources attached to a node installation
     (configuration files, log files, docker volumes etc).
  -  Added option to specify configuration file path when running
     ``vnode create-private-key``.

-  **Bugfix**

  -  Fixed swagger docs
  -  Improved error message if docker is not running when a node is
     started
  -  Improved error message for ``vserver version`` and
     ``vnode version`` if no servers or nodes are running
  -  Patching user failed if users had zero roles - this has been
     fixed.
  -  Creating roles was not possible for a user who had permission to
     create roles only for their own organization - this has been
     corrected.

3.0.0
-----

-  **Feature**

  -  Direct algorithm-to-algorithm communication has been added. Via a
     VPN connection, algorithms can exchange information with one
     another.
  -  Pagination is added. Metadata is provided in the headers by
     default. It is also possible to include them in the output body by
     supplying an additional parameter\ ``include=metadata``.
     Parameters ``page`` and ``per_page`` can be used to paginate. The
     following endpoints are enabled:

     -  GET ``/result``
     -  GET ``/collaboration``
     -  GET ``/collaboration/{id}/organization``
     -  GET ``/collaboration/{id}/node``
     -  GET ``/collaboration/{id}/task``
     -  GET ``/organization``
     -  GET ``/role``
     -  GET ``/role/{id}/rule``
     -  GET ``/rule``
     -  GET ``/task``
     -  GET ``/task/{id}/result``
     -  GET ``/node``

  -  API keys are encrypted in the database
  -  Users cannot shrink their own permissions by accident
  -  Give node permission to update public key
  -  Dependency updates

-  **Bugfix**

  -  Fixed database connection issues
  -  Don’t allow users to be assigned to non-existing organizations by
     root
  -  Fix node status when node is stopped and immediately started up
  -  Check if node names are allowed docker names


2.3.0 - 2.3.4
-------------

-  **Feature**

  -  Allows for horizontal scaling of the server instance by adding
     support for RabbitMQ. Note that this has not been released for
     version 3(!)

-  **Bugfix**

  -  Performance improvements on the ``/organization`` endpoint

2.2.0
-----

-  **Feature**

  -  Multi-database support for nodes. It is now possible to assign
     multiple data sources to a single node. The user can request a
     specific data source by supplying the *database* argument when
     creating a task.
  -  The mailserver now supports TLS and SSL options

-  **Bugfix**

  -  Nodes are now disconnected more gracefully. This fixes the issue
     that nodes appear offline while they are in fact online
  -  Fixed a bug that prevented deleting a node from the collaboration
  -  A role is now allowed to have zero rules
  -  Some http error messages have improved
  -  Organization fields can now be set to an empty string

2.1.2 & 2.1.3
-------------

-  **Bugfix**

  -  Changes to the way the application interacts with the database.
     Solves the issue of unexpected disconnects from the DB and thereby
     freezing the application.

2.1.1
-----

-  **Bugfix**

  -  Updating the country field in an organization works again\\
  -  The ``client.result.list(...)`` broke when it was not able to
     deserialize one of the in- or outputs.

2.1.0
-----

-  **Feature**

  -  Custom algorithm environment variables can be set using the
     ``algorithm_env`` key in the configuration file. `See this Github
     issue <https://github.com/IKNL/vantage6-node/issues/32>`__.
  -  Support for non-file-based databases on the node. `See this Github
     issue <https://github.com/IKNL/vantage6/issues/66>`__.
  -  Added flag ``--attach`` to the ``vserver start`` and
     ``vnode start`` command. This directly attaches the log to the
     console.
  -  Auto updating the node and server instance is now limited to the
     major version. `See this Github
     issue <https://github.com/IKNL/vantage6/issues/65>`__.

     -  e.g. if you’ve installed the Trolltunga version of the CLI you
        will always get the Trolltunga version of the node and server.
     -  Infrastructure images are now tagged using their version major.
        (e.g. ``trolltunga`` or ``harukas`` )
     -  It is still possible to use intermediate versions by specifying
        the ``--image`` option when starting the node or server.
        (e.g. ``vserver start --image harbor.vantage6.ai/infrastructure/server:2.0.0.post1``
        )

-  **Bugfix**

  -  Fixed issue where node crashed if the database did not exist on
     startup. `See this Github
     issue <https://github.com/IKNL/vantage6/issues/67>`__.

2.0.0.post1
-----------

-  **Bugfix**

  -  Fixed a bug that prevented the usage of secured registry
     algorithms

2.0.0
-----

-  **Feature**

  -  Role/rule based access control

     -  Roles consist of a bundle of rules. Rules profided access to
        certain API endpoints at the server.
     -  By default 3 roles are created: 1) Container, 2) Node, 3) Root.
        The root role is assigned to the root user on the first run.
        The root user can assign rules and roles from there.
  -  Major update on the *python*-client. The client also contains
     management tools for the server (i.e. to creating users,
     organizations and managing permissions. The client can be imported
     from ``from vantage6.client import Client`` .
  -  You can use the agrument ``verbose`` on the client to output
     status messages. This is usefull for example when working with
     Jupyter notebooks.
  -  Added CLI ``vserver version`` , ``vnode version`` ,
     ``vserver-local version`` and ``vnode-local version`` commands to
     report the version of the node or server they are running
  -  The logging contains more information about the current setup, and
     refers to this documentation and our Discourd channel

-   **Bugfix**

  -  Issue with the DB connection. Session management is updated. Error
     still occurs from time to time but can be reset by using the
     endpoint ``/health/fix`` . This will be patched in a newer
     version.

1.2.3
-----

-  **Feature**

  -  The node is now compatible with the Harbor v2.0 API


1.2.2
-----

-  **Bug fixes**

  -  Fixed a bug that ignored the ``--system`` flag from
     ``vnode start``
  -  Logging output muted when the ``--config`` option is used in
     ``vnode start``
  -  Fixed config folder mounting point when the option ``--config``
     option is used in ``vnode start``

1.2.1
-----

-  **Bug fixes**

  -  starting the server for the first time resulted in a crash as the
     root user was not supplied with an email address.
  -  Algorithm containers could still access the internet through their
     host. This has been patched.

1.2.0
-----

-  **Features**

  -  Cross language serialization. Enabling algorithm developers to
     write algorithms that are not language dependent.
  -  Reset password is added to the API. For this purpose two endpoints
     have been added: ``/recover/lost``\ and ``recover/reset`` . The
     server config file needs to extended to be connected to a
     mail-server in order to make this work.
  -  User table in the database is extended to contain an email address
     which is mandatory.

-  **Bug fixes**

  -  Collaboration name needs to be unique
  -  API consistency and bug fixes:

     -  GET ``organization`` was missing domain key
     -  PATCH ``/organization`` could not patch domain
     -  GET ``/collaboration/{id}/node`` has been made consistent with
        ``/node``
     -  GET ``/collaboration/{id}/organization`` has been made
        consistent with ``/organization``
     -  PATCH ``/user`` root-user was not able to update users
     -  DELETE ``/user`` root-user was not able to delete users
     -  GET ``/task`` null values are now consistent: ``[]`` is
        replaced by ``null``
     -  POST, PATCH, DELETE ``/node`` root-user was not able to perform
        these actions
     -  GET ``/node/{id}/task`` output is made consistent with the

-  **other**

  -  ``questionairy`` dependency is updated to 1.5.2
  -  ``vantage6-toolkit`` repository has been merged with the
     ``vantage6-client`` as they were very tight coupled.

1.1.0
-----

-  **Features**

  -  new command ``vnode clean`` to clean up temporary docker volumes
     that are no longer used
  -  Version of the individual packages are printed in the console on
     startup
  -  Custom task and log directories can be set in the configuration
     file
  -  Improved **CLI** messages
  -  Docker images are only pulled if the remote version is newer. This
     applies both to the node/server image and the algorithm images
  -  Client class names have been simplified (``UserClientProtocol`` ->
     ``Client``)

-  **Bug fixes**

  -  Removed defective websocket watchdog. There still might be
     disconnection issues from time to time.

1.0.0
-----

-  **Updated Command Line Interface (CLI)**

  -  The commands ``vnode list`` , ``vnode start`` and the new
     command\ ``vnode attach`` are aimed to work with multiple nodes at
     a single machine.
  -  System and user-directories can be used to store configurations by
     using the ``--user/--system`` options. The node stores them by
     default at user level, and the server at system level.
  -  Current status (online/offline) of the nodes can be seen using
     ``vnode list`` , which also reports which environments are
     available per configuration.
  -  Developer container has been added which can inject the container
     with the source. ``vnode start --develop [source]``. Note that
     this Docker image needs to be build in advance from the
     ``development.Dockerfile`` and tag ``devcon``.
  -  ``vnode config_file`` has been replaced by ``vnode files`` which
     not only outputs the config file location but also the database
     and log file location.

-  **New database model**

  -  Improved relations between models, and with that, an update of the Python
     API.
  -  Input for the tasks is now stored in the result table. This was
     required as the input is encrypted individually for each
     organization (end-to-end encryption (E2EE) between organizations).
  -  The ``Organization`` model has been extended with the
     ``public_key`` (String) field. This field contains the public key
     from each organization, which is used by the E2EE module.
  -  The ``Collaboration`` model has been extended with the
     ``encrypted`` (Boolean) field which keeps track if all messages
     (tasks, results) need to be E2EE for this specific collaboration.
  -  The ``Task`` keeps track of the initiator (organization) of the
     organization. This is required to encrypt the results for the
     initiator.

-  **End to end encryption**

  -  All messages between all organizations are by default be
     encrypted.
  -  Each node requires the private key of the organization as it needs
     to be able to decrypt incoming messages. The private key should be
     specified in the configuration file using the ``private_key``
     label.
  -  In case no private key is specified, the node generates a new key
     an uploads the public key to the server.
  -  If a node starts (using ``vnode start``), it always checks if the
     ``public_key`` on the server matches the private key the node is
     currently using.
  -  In case your organization has multiple nodes running they should
     all point to the same private key.
  -  Users have to encrypt the input and decrypt the output, which can
     be simplified by using our client ``vantage6.client.Client`` \_\_
     for Python \_\_ or ``vtg::Client`` \_\_ for R.
  -  Algorithms are not concerned about encryption as this is handled
     at node level.

-  **Algorithm container isolation**

  -  Containers have no longer an internet connection, but are
     connected to a private docker network.
  -  Master containers can access the central server through a local
     proxy server which is both connected to the private docker network
     as the outside world. This proxy server also takes care of the
     encryption of the messages from the algorithms for the intended
     receiving organization.
  -  In case a single machine hosts multiple nodes, each node is
     attached to its own private Docker network.

-  **Temporary Volumes**

  -  Each algorithm mounts temporary volume, which is linked to the
     node and the ``job_id`` of the task
  -  The mounting target is specified in an environment variable
     ``TEMPORARY_FOLDER``. The algorithm can write anything to this
     directory.
  -  These volumes need to be cleaned manually.
     (``docker rm VOLUME_NAME``)
  -  Successive algorithms only have access to the volume if they share
     the same ``job_id`` . Each time a **user** creates a task, a new
     ``job_id`` is issued. If you need to share information between
     containers, you need to do this through a master container. If a
     central container creates a task, all child tasks will get the
     same ``job_id``.

-  **RESTful API**

  -  All RESTful API output is HATEOS formatted.
      **(**\ `wiki <https://en.wikipedia.org/wiki/HATEOAS>`__\ **)**

-  **Local Proxy Server**

  -  Algorithm containers no longer receive an internet connection.
     They can only communicate with the central server through a local
     proxy service.
  -  It handles encryption for certain endpoints (i.e. ``/task``, the
     input or ``/result`` the results)

-  **Dockerized the Node**

  -  All node code is run from a Docker container. Build versions can
     be found at our Docker repository:
     ``harbor.distributedlearning.ai/infrastructure/node`` . Specific
     version can be pulled using tags.
  -  For each running node, a Docker volume is created in which the
     data, input and output is stored. The name of the Docker volume
     is: ``vantage-NODE_NAME-vol`` . This volume is shared with all
     incoming algorithm containers.
  -  Each node is attached to the public network and a private network:
     ``vantage-NODE_NAME-net``.
