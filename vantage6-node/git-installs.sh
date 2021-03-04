# install vantage6 dependancies from github on the same branch. This is usefull
# as some test fail due to a vantage6-dependancy.
pip install git+https://github.com/iknl/vantage6@$TRAVIS_BRANCH
pip install git+https://github.com/iknl/vantage6-common@$TRAVIS_BRANCH
pip install git+https://github.com/iknl/vantage6-client@$TRAVIS_BRANCH
pip install git+https://github.com/iknl/vantage6-server@$TRAVIS_BRANCH