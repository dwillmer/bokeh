_ = require "underscore"
$ = require "jquery"
$1 = require "bootstrap/button"
ContinuumView = require "../../common/continuum_view"
Model = require "../../model"

class CheckboxButtonGroupView extends ContinuumView
  tagName: "div"
  events:
    "change input": "change_input"

  initialize: (options) ->
    super(options)
    @render()
    @listenTo(@model, 'change', @render)

  render: () ->
    @$el.empty()

    @$el.addClass("bk-bs-btn-group")
    @$el.attr("data-bk-bs-toggle", "buttons")

    active = @mget("active")
    for label, i in @mget("labels")
      $input = $('<input type="checkbox">').attr(value: "#{i}")
      if i in active then $input.prop("checked", true)
      $label = $('<label class="bk-bs-btn"></label>')
      $label.text(label).prepend($input)
      $label.addClass("bk-bs-btn-" + @mget("type"))
      if i in active then $label.addClass("bk-bs-active")
      @$el.append($label)

    return @

  change_input: () ->
    active = (i for checkbox, i in @$("input") when checkbox.checked)
    @mset('active', active)
    @mget('callback')?.execute(@model)

class CheckboxButtonGroup extends Model
  type: "CheckboxButtonGroup"
  default_view: CheckboxButtonGroupView

  defaults: () ->
    return _.extend {}, super(), {
      active: []
      labels: []
      type: "default"
      disabled: false
    }

module.exports =
  Model: CheckboxButtonGroup
  View: CheckboxButtonGroupView
