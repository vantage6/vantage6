var FontFaceObserver = require('fontfaceobserver')

module.exports = {
  apply: function(terminalConstructor) {
    terminalConstructor.prototype.loadWebfontAndOpen = function(element) {
      var _this = this

      var fontFamily = this.getOption('fontFamily')
      var regular = new FontFaceObserver(fontFamily).load()
      var bold = new FontFaceObserver(fontFamily, { weight: 'bold' }).load()

      return regular.constructor.all([regular, bold]).then(
        function() {
          _this.open(element)
          return _this
        },
        function() {
          _this.setOption('fontFamily', 'Courier')
          _this.open(element)
          return _this
        }
      )
    }
  }
}
