Preprocessing
------------------

With preprocessing you can transform your data before it is passed to an algorithm.

Setting up preprocessing
++++++++++++++++++++++++
Before being able to use an algorithm on your date you may need to do
preprocessing. Vantage6 supports with by adding a "preprocessing"
field to your dataset's configuration dictionary. This field should contain an
ordered list of preprocessingsteps to be taken, each represented as its own
dictionary.

Within each step's dictionary, you'll find two key-value pairs:

1. function: A string specifying the function to be used for preprocessing.
2. parameters: Another dictionary that contains all the necessary parameters
   for the aforementioned function.

The steps will be carried out sequentially, in the order they appear in the list.



An example of a task with dataset preprocessing:

.. code:: python

   input_ = {'method': 'central_average',
            'kwargs': {'column_name': 'age'}}

   average_task = userclient.task.create(
      collaboration=1,
      organizations=[1],
      name="filtered_average",
      image="v4-average",
      description='average with filters',
      input=input_,
      databases=[{
         'label': 'default',
         'preprocessing': [{
            'function': 'select_rows',
            'parameters': {'query': 'age>50'}
         }]
      }])

.. note::

   In case you want to test your preprocessing in an AlgorithmMockClient, you can
   create and test the preprocessing using the following code:

   .. code:: python

       import pandas as pd
       from vantage6.algorithm.tools.mock_client import MockAlgorithmClient
 
       # Create a dictionary with sample data
       data = {
          'age': [23, 45, 67, 34, 28, 59, 32, 41, 24, 77],
          'gender': ['M', 'F', 'M', 'F', 'M', 'F', 'F', 'M', 'F', 'M'],
          'icd-10 code': ['A00', 'B12', 'C43', 'D25', 'E10', 'F33', 'G12', 'H45', 'I20', 'J31']
       }
  
       # Create a DataFrame
       df = pd.DataFrame(data)

       print(df)


       datasets = [
             [
                 {
                     "database": dataset,
                     "type_": "csv",
                     "preprocessing": [
                         {
                             "function": "select_rows",
                             "parameters": {"query": "age>50"},
                         },
                     ],
                 }
                 for dataset in [df]
             ]
         ]
 
       mockclient = MockAlgorithmClient(
             datasets=datasets, module="mock_package"
       )

       org_ids = [org["id"] for org in mockclient.organization.list()]

       input_ = {"method": "execute", "kwargs": {}}
       child_task = mockclient.task.create(
           organizations=org_ids,
           input_=input_,
       )

       result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))

       print(result)

   The output of this code is:

   The inital DataFrame:

   ====  =====  ========  =============
   ..    age    gender    icd-10 code
   ====  =====  ========  =============
      0     23  M         A00
      1     45  F         B12
      2     67  M         C43
      3     34  F         D25
      4     28  M         E10
      5     59  F         F33
      6     32  F         G12
      7     41  M         H45
      8     24  F         I20
      9     77  M         J31
   ====  =====  ========  =============

   The filtered DataFrame:

   ====  =====  ========  =============
   ..    age    gender    icd-10 code
   ====  =====  ========  =============
      2     67  M         C43
      5     59  F         F33
      9     77  M         J31
   ====  =====  ========  =============


Syntax
+++++++++++++++++++++++


Functionalities
+++++++++++++++++++++++

Examples
+++++++++++++++++++++++