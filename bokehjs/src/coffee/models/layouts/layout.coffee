_ = require "underscore"
Component = require "../component"

class Layout extends Component.Model
  type: "Layout"

  defaults: ->
    return _.extend {}, super(), {
      width: null
      height: null
    }

module.exports =
  Model: Layout
