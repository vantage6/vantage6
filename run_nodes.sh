docker restart local-registry
docker restart azurite
docker build . -f ./docker/algorithm-base.Dockerfile -t large-data-test-algorithm-base:latest
docker build ~/source/large-data-test/dhd-test-algorithm/ -t localhost:5000/dhd-test-algorithm:latest
docker push localhost:5000/dhd-test-algorithm:latest
docker build . -f ./docker/node-and-server.Dockerfile -t large-node:latest
rm -f /home/thendriks/.cache/vantage6/log/node/alpha/node_user.log
rm -f /home/thendriks/.cache/vantage6/log/node/gamma/node_user.log
rm -f /home/thendriks/.cache/vantage6/log/node/beta/node_user.log
vnode stop --name alpha 
vnode stop --name beta
vnode stop --name gamma
vnode start --name alpha --image large-node:latest --debug-port 5680
vnode start --name beta --image large-node:latest --debug-port 5679
vnode start --name gamma --image large-node:latest --debug-port 5678
vserver stop --name test-server
vserver start --name test-server --image large-node:latest
docker logs vantage6-alpha-user -f
