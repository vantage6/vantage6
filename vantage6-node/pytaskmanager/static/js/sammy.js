// app.js
function default_value(value) {
    return function() {
        return value;
    };
};


function redirect_if_no_access(ctx) {
    console.log(ctx.verb, ctx.path);

    var access_token  = ctx.session('access_token', default_value(''));

    if (access_token == '') {
        ctx.redirect('#/login/');
    }
}

(function($) {
    $.ajaxSetup({
        dataType: 'json',
        contentType: 'application/json',
        processData: false,
        beforeSend: function(jqXHR, options) {
            if (options.contentType == "application/json" && typeof options.data != "string") {
                options.data = JSON.stringify(options.data);
            }

            var token = localStorage.getItem('access_token');
            if (token) {
                jqXHR.setRequestHeader('Authorization', 'Bearer ' + token);
            }
        }
    });
      
    var app = $.sammy('#main', function() {
        this.use('Mustache', 'html');
        this.use('Session');

        this.get('#/', function(ctx) {
            redirect_if_no_access(ctx);

            var access_token  = this.session('access_token', default_value(''));
            console.log('access_token:', access_token);

            ctx.redirect('#/dashboard/');
        });


        this.get('#/login/', function(ctx) {
            console.log(ctx.verb, ctx.path);

            var username  = this.session('username', default_value(''));
            console.log('username', username);

            ctx.partial(
                'templates/login.tpl.html', 
                { username: username },
                function() {
                    $('#login-form').fadeIn(200);
                }
            );
        });

        this.get('#/logout/', function(ctx) {
            console.log(ctx.verb, ctx.path);

            ctx.session('username', '');
            ctx.session('access_token', '');
            ctx.session('refresh_token', '');
            ctx.session('refresh_url', '');
            ctx.session('user_url', '');

            redirect_if_no_access(ctx);
        });


        this.post('#/login/', function(ctx) {
            console.log(ctx.verb, ctx.path);

            // POST form data to server.
            $.post({
                url: "/api/token",
                data: {
                    username: ctx.params.username, 
                    password: ctx.params.password
                },
            })
            .done(function(data) {
                console.log("successfully authenticated!");
                ctx.session('username', ctx.params.username);
                ctx.session('access_token', data.access_token);
                ctx.session('refresh_token', data.refresh_token);
                ctx.session('refresh_url', data.refresh_url);
                ctx.session('user_url', data.user_url);

                $('#login-form').fadeOut(200, function() {
                    console.log('redirecting to "/"');
                    ctx.redirect('#/');
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
        });

        this.get('#/dashboard/', function(ctx) {
            redirect_if_no_access(ctx);

            var data = {
                username: this.session('username', default_value(''))
            }

            Terminal.applyAddon(fit);

            var token = ctx.session('access_token', default_value(''))
            var socket_options = {
              transportOptions: {
                polling: {
                  extraHeaders: {
                    Authorization: "Bearer " + token
                  }
                }
              }
            }


            function connect_websocket_pty(ctx) {
                console.log('connecting to websocket /pty');
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
                      console.log('key:', key);
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


            function connect_websocket_admin(ctx) {
                console.log('connecting to websocket /admin');
                var socket = io.connect('/admin', socket_options);
                socket.on('connect', function() {
                    console.log('connected websocket to /admin')

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
                        term.writeln(data)
                    })

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

            ctx.partial(
                'templates/dashboard.tpl.html', 
                data, 
                function() {
                    $('.dashboard-content').fadeIn(function() {
                        connect_websocket_pty(ctx);
                        connect_websocket_admin(ctx);

                    });

                }
            );
        });

    });
  
    // Run the application!
    $(function() {
        app.run('#/');
        console.log('current window width: ', $('body').width());
    }); 
      
})(jQuery);