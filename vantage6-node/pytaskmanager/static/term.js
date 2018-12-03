
window.addEventListener('load', function() {
  var token = '';
  var socket = io.connect(
    '/pty', 
    {
      transportOptions: {
        polling: {
          extraHeaders: {
            Authorization: "Bearer " + token
          }
        }
      }
    }
  );

  socket.on('connect', function() {
    Terminal.applyAddon(fit)
    var term = new Terminal({
      // cols: 80,
      // rows: 24,
      screenKeys: true,
      cursorBlink: true,
      cursorStyle: "underline",
      fontSize: 12
      // fontFamily: 'Ubuntu Mono, courier-new, courier, monospace'
    });


    // define event handlers
    term.on('key', (key, ev) => {
      // console.log("pressed key", key)
      // console.log("event", ev)
      socket.emit("pty-input", {"input": key})
    });

    term.on('title', function(title) {
      console.log('title:', title)
      document.title = title;
    });

    socket.on("pty-output", function(data){
      // console.log("new output", data)
      term.write(data.output)
    })

    socket.on('disconnect', function() {
      console.log("disconnected!!!!")
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

    function fitToscreen(){
      term.fit()
      socket.emit("resize", {"cols": term.cols, "rows": term.rows})
    }


    // open the terminal
    term.open(document.getElementById('terminal'));
    const wait_ms = 50;
    window.onresize = debounce(fitToscreen, wait_ms)

    // term.toggleFullScreen(true)
    term.fit();

    // document.getElementById("terminal").focus();
    term.textarea.focus();
    term.writeln('-'.repeat(80))
    term.writeln('Connected to interpreter. Hit [enter] if the screen remains blank.')
    term.writeln('-'.repeat(80))
  });
}, false);


