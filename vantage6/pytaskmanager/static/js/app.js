'use strict';

$.ajaxPrefilter(function(options, originalOptions, jqXHR) {
    if (options.url != '/api/token') {
        var token = localStorage.getItem('access_token');
        if (token) {
            console.log('setting access token to ajax request');
            jqXHR.setRequestHeader('Authorization', 'Bearer ' + token);

        } else {
            console.log('no token available ...');
        }
    }
});

$.ajaxSetup({
    dataType: 'json',
    contentType: 'application/json',
    processData: false,
    beforeSend: function(jqXHR, options) {
        if (options.contentType == "application/json" && typeof options.data != "string") {
            options.data = JSON.stringify(options.data);
        }
    }
});


class Application extends React.Component {
    constructor(props) {
        super(props);

        this.storage = window.localStorage;

        this.state = {
            access_token: this.storage.getItem('access_token'),
            refresh_token: '',
            username: this.storage.getItem('username') || ''
        };     

        this.onLogin = this.onLogin.bind(this);
        this.onLogout = this.onLogout.bind(this);
    }

    onLogin(username, access_token, refresh_token) {
        console.log('onLogin: ', username);
        console.log('setting state ... ');

        this.setState({
            username: username,
            access_token: access_token,
            refresh_token: refresh_token
        });

        this.storage.setItem('username', username);
        this.storage.setItem('access_token', access_token);
    };

    onLogout() {
        console.log('onLogout: ', this.state.username);

        this.setState({
            access_token: '',
            refresh_token: ''
        });

        this.storage.setItem('access_token', '');        
        this.storage.setItem('refresh_token', '');        
    }

    render() {
        if (this.state.access_token) {
            return(
                <Dashboard 
                    app={this}
                    username={this.state.username}
                    onLogout={this.onLogout}
                    />
            )
        }

        // console.log('No access token, displaying login screen!');
        return(
            <Login 
                username={this.state.username}
                onLogin={this.onLogin}
                />
        )
    };
};

class Login extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
          username: props.username,
          password: ''
        };

        // FIXME: this is ugly. wondering if there's another way?
        this.updateUsername = this.updateUsername.bind(this);
        this.updatePassword = this.updatePassword.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
    };

    updateUsername(event) {
        this.setState({username: event.target.value});
    }

    updatePassword(event) {
        this.setState({password: event.target.value}); 
    }

    handleSubmit(event) {
        //alert('The form was submitted: ' + this.state.value);
        // this.props.handleLogin(this.state.username, this.state.password);
        const username = this.state.username;
        const password = this.state.password;
        const ctx = this;

        $.post({
            url: "/api/token",
            data: {
                username: username, 
                password: password
            },
        })
        .done(function(data) {
            console.log("successfully authenticated!");
            ctx.setState({username: username});
            ctx.setState({access_token: data.access_token});
            ctx.setState({refresh_token: data.refresh_token});
            ctx.setState({refresh_url: data.refresh_url});
            ctx.setState({user_url: data.user_url});

            $('#login-form').fadeOut(200, function() {
                console.log('notifying Application ...')
                ctx.props.onLogin(
                    username, 
                    data.access_token, 
                    data.refresh_token
                );
            });
        })
        .fail(function(data) {
            console.log("failure:", data);
            var color = $('#login-form').css('border-color');
            var duration = 200;
            $('#login-form').animate({borderColor: '#f00'}, duration, function() {
                $('#login-form').animate({borderColor: color}, duration);
            });
        });

        event.preventDefault();
    };

    render() {
        return (
            <div className="login-content">
               <div id="login-form">

                 <form onSubmit={this.handleSubmit}>
                   <div className="form-group">
                     <label>username</label>
                     <input type="username" className="form-control" placeholder="username"value={this.state.username}onChange={this.updateUsername}/>
                   </div>

                   <div className="form-group">
                     <label>password</label>
                     <input type="password" className="form-control" placeholder="password"value={this.state.password}onChange={this.updatePassword}/>
                   </div>

                   <button type="submit" className="btn btn-primary">Submit</button>
                 </form>

               </div>
             </div>    
        );
    }
};

class DashboardBlankDisplay extends React.Component {
    render() {
        return(
            <div>
                <div className="dashboard-header">
                    cheddar header
                </div>
                <div>blank</div>
            </div>
        )
    }
};

class DashboardNavDisplay extends React.Component {
    render() {
        return(
            <div className="dashboard-nav">
                <span>user: <b>{this.props.username}</b></span>
                <span className="logout"><a href="" onClick={this.props.onLogout}>logout</a></span>
            </div>
        ) 
    }
};

class DashboardNodeDisplay extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            access_token: localStorage.getItem('access_token')
        };
    }

    updateState(ctx) {
        $.get({
            url: '/api/stats'
        }).done(function(data) {
            ctx.setState({
                'collaborations': data.collaborations
            });
        });
    }

    componentDidMount() {
        var socket = this.props.socket;
        var ctx = this;

        socket.on('connect', function() {
            socket.on("node-status-changed", function(data) {
                console.log('node-status-changed', data);
                ctx.updateState(ctx);
            });            
        });

        this.updateState(this);
    }

    renderNode(node) {
        var status;

        if (node.status == 'online') {
            status = <span className='small right green'>online</span>
        } else {
            status = <span className='small right red'>offline</span>
        }

        return(
            <div key={node.id}>
                <span className="small">{node.organization.name}</span>
                {status}
            </div>
        )
    }

    renderCollaboration(collaboration) {
        var nodes = [];
        for (var idx in collaboration.nodes) {
            nodes.push(this.renderNode(collaboration.nodes[idx]));
        }

        return(
            <div key={collaboration.id} className="dashboard-collaboration">
                <h4>{collaboration.name}</h4>
                {nodes}
            </div>
        )
    }

    render() {
        const collaborations = this.state.collaborations;
        var rc = [];

        for (var idx in collaborations) {
            rc.push(this.renderCollaboration(collaborations[idx]));
        }

        return(
            <div>
                <div className="dashboard-header">
                    Collaborations
                </div>
                <div>{rc}</div>
            </div>
        );
    };
};

class DashboardTerminalDisplay extends React.Component {
    constructor(props) {
        super(props);
        this.app = props.app;

        Terminal.applyAddon(fit);
    }

    componentDidMount() {
        var token = localStorage.getItem('access_token');
        var socket_options = {
          transportOptions: {
            polling: {
              extraHeaders: {
                Authorization: "Bearer " + token
              }
            }
          }
        };

        var socket = io.connect('/pty', socket_options);
        socket.on('connect', function() {
            var term = new Terminal({
              screenKeys: true,
              cursorBlink: true,
              cursorStyle: "underline",
              fontSize: 11,
              fontFamily: 'fira_mono',
              theme: {
                background: '#0e1326'
              }
            });

            // define event handlers
            term.on('key', (key, ev) => {
              socket.emit("pty-input", {"input": key})
            });

            term.on('title', function(title) {
              console.log('title:', title)
              document.title = title;
            });

            socket.on("pty-output", function(data) {
              term.write(data.output)
            })

            socket.on('disconnect', function() {
              console.log("disconnected pty!!!!")
              term.destroy();
              socket.close();
              socket.open();
            });


            function debounce(func, wait_ms) {
              let timeout
              return function(...args) {
                const context = this
                clearTimeout(timeout)
                timeout = setTimeout(() => func.apply(context, args), wait_ms)
              }
            }

            function fitToscreen() {
              term.fit()
              socket.emit("resize", {"cols": term.cols, "rows": term.rows})
            }

            // open the terminal
            term.open(document.getElementById('terminal'));
            const wait_ms = 50;
            window.onresize = debounce(fitToscreen, wait_ms);

            // term.toggleFullScreen(true)
            term.fit();

            term.textarea.focus();
            term.writeln('-'.repeat(80));
            term.writeln('Connected to interpreter. Hit [enter] if the screen remains blank.');
            term.writeln('-'.repeat(80));                
        });

    }    

    render() {
        return(
            <div>
                <div className="dashboard-header">
                    terminal
                </div>
                <div id="terminal">
                </div>
            </div>
        ) 
    }
};

class DashboardLogDisplay extends React.Component {
    constructor(props) {
        super(props);
        this.app = props.app;

        Terminal.applyAddon(fit);
    }

    componentDidMount() {
        var socket = this.props.socket;
        socket.on('connect', function() {
            var term = new Terminal({
              screenKeys: true,
              cursorBlink: true,
              cursorStyle: "underline",
              fontSize: 11,
              fontFamily: 'fira_mono',
              theme: {
                background: '#0e1326'
              }
            });

            // define event handlers
            socket.on("append-log", function(data) {
                term.writeln(data);
            });

            socket.on('disconnect', function() {
              console.log("disconnected /admin!!!!")
              term.destroy();
              socket.close();
              socket.open();
            });

            function debounce(func, wait_ms) {
              let timeout
              return function(...args) {
                const context = this
                clearTimeout(timeout)
                timeout = setTimeout(() => func.apply(context, args), wait_ms)
              }
            }

            function fitToscreen() {
              term.fit()
              socket.emit("resize", {"cols": term.cols, "rows": term.rows})
            }

            // open the terminal
            term.open(document.getElementById('log'));
            const wait_ms = 50;
            window.onresize = debounce(fitToscreen, wait_ms);

            term.fit();
        });
    }

    render() {
        return(
            <div>
                <div className="dashboard-header">
                    log
                </div>
                <div id="log">
                </div>
            </div>
        ) 
    };
};

class DashboardGlobeDisplay extends React.Component {
    componentDidMount() {
        //this.renderGlobe();
        this.renderEncomGlobe();
    }

    renderEncomGlobe() {
        const width = $('#globe').width();
        const height = $('#globe').height();

        var globe = new ENCOM.Globe(width, height, {
            font: "monaco",
            data: data.slice(), 
            tiles: grid.tiles,
            baseColor: 'cyan',
            markerColor: 'yellow',
            pinColor: 'cyan',
            satelliteColor: 'orange',
            scale: 1,
            dayLength: 1000 * 30,
            introLinesDuration: 2000,
            maxPins: 500,
            maxMarkers: 500,
            viewAngle: 0
        });

        $("#globe").append(globe.domElement);
        globe.init(start);
        // console.log('-'.repeat(80));
        // console.log(globe.renderer);
        // console.log('-'.repeat(80));
        globe.renderer.setClearColor('#121831');

        function animate(){

            if(globe){
                globe.tick();
            }

            requestAnimationFrame(animate);
        }

        function start(){
            animate();

            /* add pins at random locations */
            setInterval(function(){
                var lat = Math.random() * 180 - 90,
                   lon = Math.random() * 360 - 180,
                   name = "Test " + Math.floor(Math.random() * 100);

                globe.addPin(lat,lon, name);

            }, 5000);

            setTimeout(function() {
                var constellation = [];
                var opts = {
                    coreColor: 'orange',
                    numWaves: 8
                };
                var alt =  1.3;

                for(var i = 0; i< 2; i++){
                    for(var j = 0; j< 3; j++){
                         constellation.push({
                            lat: 50 * i - 30 + 15 * Math.random(), 
                             lon: 120 * j - 120 + 30 * i, 
                             altitude: alt
                             });
                    }
                }

                globe.addConstellation(constellation, opts);
            }, 4000);

            /* add the connected points that are in the movie */
            setTimeout(function(){
                globe.addMarker(49.25, -123.1, "Vancouver");
                globe.addMarker(35.6895, 129.69171, "Tokyo", true);
            }, 2000);
        }

    }

    renderGlobe() {
        // Parameters
        const width = $('#globe').width();
        const height = $('#globe').height();
        var webglEl = document.getElementById('globe');

        var radius = 0.5,
            segments = 32,
            rotation = 6;  

        var scene = new THREE.Scene();

        var camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 1000);
        camera.position.z = 1.5;

        var renderer = new THREE.WebGLRenderer();
        renderer.setSize(width, height);

        scene.add(new THREE.AmbientLight(0x333333));

        var light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(5,3,5);
        scene.add(light);

        var sphere = createSphere(radius, segments);
        sphere.rotation.y = rotation; 
        scene.add(sphere);

        // var clouds = createClouds(radius, segments);
        // clouds.rotation.y = rotation;
        // scene.add(clouds);

        // var stars = createStars(90, 64);
        // scene.add(stars);

        // var controls = new THREE.TrackballControls(camera);

        webglEl.appendChild(renderer.domElement);
        render_frame()

        function render_frame() {
            // controls.update();
            sphere.rotation.y += 0.0015;
            // clouds.rotation.y += 0.0005;    
            requestAnimationFrame(render_frame);
            renderer.render(scene, camera);
        }

        function createSphere(radius, segments) {
            return new THREE.Mesh(
                new THREE.SphereGeometry(radius, segments, segments),
                new THREE.MeshPhongMaterial({
                    // map:         THREE.ImageUtils.loadTexture('img/map_outline.png')
                    map:         THREE.ImageUtils.loadTexture('img/2_no_clouds_4k.jpg')
                    // bumpMap:     THREE.ImageUtils.loadTexture('img/elev_bump_4k.jpg'),
                    // bumpScale:   0.005,
                    // specularMap: THREE.ImageUtils.loadTexture('img/water_4k.png'),
                    // specular:    new THREE.Color('grey')                
              })
            );
        }

        function createClouds(radius, segments) {
            return new THREE.Mesh(
                new THREE.SphereGeometry(radius + 0.003, segments, segments),     
                new THREE.MeshPhongMaterial({
                    map:         THREE.ImageUtils.loadTexture('img/fair_clouds_4k.png'),
                    transparent: true
                })
            );    
        }

        function createStars(radius, segments) {
            return new THREE.Mesh(
                new THREE.SphereGeometry(radius, segments, segments), 
                new THREE.MeshBasicMaterial({
                    map:  THREE.ImageUtils.loadTexture('img/galaxy_starfield.png'), 
                    side: THREE.BackSide
                })
            );
        }        
    }

    render() {
        return(
            <div>
                <div className="dashboard-header">
                    World view
                </div>
                <div id="globe"></div>
            </div>
        )
    }
}

class Dashboard extends React.Component {
    constructor(props) {
        super(props);
        this.app = props.app;

        var token = localStorage.getItem('access_token');
        var socket_options = {
          transportOptions: {
            polling: {
              extraHeaders: {
                Authorization: "Bearer " + token
              }
            }
          }
        };

        this.state = {
            admin_socket: io.connect('/admin', socket_options)
        };
    }

    componentDidMount() {
    }

    render() {
        return(
            <div className="dashboard-outer">
                <DashboardNavDisplay 
                    username={this.props.username} 
                    onLogout={this.props.onLogout}
                    />

                <div className="dashboard-content">

                    <div className="row">
                        <div className="col-3">
                            <DashboardNodeDisplay
                                app={this.app} 
                                socket={this.state.admin_socket}
                            />
                        </div>

                        <div className="col-6">
                            <DashboardTerminalDisplay
                                app={this.app} 
                            />
                        </div>

                        <div className="col-3">
                            <DashboardGlobeDisplay 
                                app={this.app}
                                socket={this.state.admin_socket}
                            />
                        </div>
                    </div>

                    <div className="row">
                        <div className="col">
                            <DashboardLogDisplay
                                app={this.app}
                                socket={this.state.admin_socket}
                            />
                        </div>
                    </div>

                </div>
            </div>
        );
    };
};


// Run the application
ReactDOM.render(
  <Application />,
  document.getElementById('main')
);


