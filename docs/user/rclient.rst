.. _r-client:

R client
--------

.. warning::
    We discourage the use of the R client. It is not actively maintained and
    is not fully implemented. It can not (yet) be used to manage resources, such
    as creating and deleting users and organizations.

.. _r client install:

Install
^^^^^^^

You can install the R client by running:

.. code:: r

   devtools::install_github('IKNL/vtg')

.. _use-R-client:

Use
^^^

The R client can only create tasks and retrieve their results.

Initialization of the R client can be done by:

.. code:: r

   setup.client <- function() {
     # Username/password should be provided by the administrator of
     # the server.
     username <- "username@example.com"
     password <- "password"

     host <- 'https://cotopaxi.vantage6.ai:443'
     api_path <- ''

     # Create the client & authenticate
     client <- vtg::Client$new(host, api_path=api_path)
     client$authenticate(username, password)

     return(client)
   }

   # Create a client
   client <- setup.client()

Then, this client can be used for the different algorithms. Refer to the
README in the repository on how to call the algorithm. Usually this
includes installing some additional client-side packages for the
specific algorithm you are using.

Example
"""""""

This example shows how to run the vantage6 implementation of a federated Cox
Proportional Hazard regression model. First you need to install the client side
of the algorithm by:

.. code:: r

   devtools::install_github('iknl/vtg.coxph', subdir="src")

This is the code to run the coxph:

.. code:: r

   print( client$getCollaborations() )

   # Should output something like this:
   #   id     name
   # 1  1 ZEPPELIN
   # 2  2 PIPELINE

   # Select a collaboration
   client$setCollaborationId(1)

   # Define explanatory variables, time column and censor column
   expl_vars <- c("Age","Race2","Race3","Mar2","Mar3","Mar4","Mar5","Mar9",
                  "Hist8520","hist8522","hist8480","hist8501","hist8201",
                  "hist8211","grade","ts","nne","npn","er2","er4")
   time_col <- "Time"
   censor_col <- "Censor"

   # vtg.coxph contains the function `dcoxph`.
   result <- vtg.coxph::dcoxph(client, expl_vars, time_col, censor_col)
