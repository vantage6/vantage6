
token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDM4Njg0NDMsIm5iZiI6MTU0Mzg2ODQ0MywianRpIjoiMDVkMGUzMDEtNzdhYS00ZDk4LWFlNjEtMTg4ZGM1N2VhZTVhIiwiZXhwIjoxNTQzOTU0ODQzLCJpZGVudGl0eSI6NCwiZnJlc2giOmZhbHNlLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9jbGFpbXMiOnsidHlwZSI6InVzZXIiLCJyb2xlcyI6WyJyb290Il19fQ.An8hEmOzutyYEb2olysA5Q5cn5RpF8GuZ4R-l_04YeE';

socket_options = {
  transportOptions: {
    polling: {
      extraHeaders: {
        Authorization: "Bearer " + token
      }
    }
  }
}


$(document).ready(function() {
  var socket = io.connect('/pty', socket_options);

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


$(document).ready(function() {
  console.log("ready!!");

  var socket = io.connect('/admin', socket_options);
  
  socket.on('connect', function() {
    console.log('connected websocket to /admin')

    Terminal.applyAddon(fit)
    var term = new Terminal({
      screenKeys: true,
      cursorBlink: true,
      cursorStyle: "underline",
      fontSize: 12
    });

    term.open(document.getElementById('log'));
    const wait_ms = 50;
    window.onresize = term.fit
    term.fit();

    socket.on("append-log", function(data){
      // console.log("append-log:", data);
      term.writeln(data);
    });
  });
});