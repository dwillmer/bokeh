_ = require "underscore"
Axis = require "./axis"
ContinuousAxis = require "./continuous_axis"
BasicTicker = require "../tickers/basic_ticker"
BasicTickFormatter = require "../formatters/basic_tick_formatter"

class LinearAxisView extends Axis.View

class LinearAxis extends ContinuousAxis.Model
  default_view: LinearAxisView
  type: 'LinearAxis'

  defaults: ->
    return _.extend {}, super(), {
      ticker: new BasicTicker.Model()
      formatter: new BasicTickFormatter.Model()
    }

module.exports =
  Model: LinearAxis
  View: LinearAxisView
