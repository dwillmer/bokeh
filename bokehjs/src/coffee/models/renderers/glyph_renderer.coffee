_ = require "underscore"
{logger} = require "../../core/logging"
Renderer = require "./renderer"
PlotWidget = require "../../common/plot_widget"
RemoteDataSource = require "../sources/remote_data_source"

class GlyphRendererView extends PlotWidget

  initialize: (options) ->
    super(options)

    @glyph = @build_glyph_view(@mget("glyph"))

    selection_glyph = @mget("selection_glyph")
    if not selection_glyph?
      selection_glyph = @mget("glyph").clone()
      selection_glyph.set(@model.selection_defaults, {silent: true})
    @selection_glyph = @build_glyph_view(selection_glyph)

    nonselection_glyph = @mget("nonselection_glyph")
    if not nonselection_glyph?
      nonselection_glyph = @mget("glyph").clone()
      nonselection_glyph.set(@model.nonselection_defaults, {silent: true})
    @nonselection_glyph = @build_glyph_view(nonselection_glyph)

    hover_glyph = @mget("hover_glyph")
    if hover_glyph?
      @hover_glyph = @build_glyph_view(hover_glyph)

    decimated_glyph = @mget("glyph").clone()
    decimated_glyph.set(@model.decimated_defaults, {silent: true})
    @decimated_glyph = @build_glyph_view(decimated_glyph)

    @xmapper = @plot_view.frame.get('x_mappers')[@mget("x_range_name")]
    @ymapper = @plot_view.frame.get('y_mappers')[@mget("y_range_name")]

    @set_data(false)

    if @mget('data_source') instanceof RemoteDataSource.Model
      @mget('data_source').setup(@plot_view, @glyph)

  build_glyph_view: (model) ->
    new model.default_view({model: model, renderer: this})

  bind_bokeh_events: () ->
    @listenTo(@model, 'change', @request_render)
    @listenTo(@mget('data_source'), 'change', @set_data)
    @listenTo(@mget('data_source'), 'stream', @set_data)
    @listenTo(@mget('data_source'), 'select', @request_render)
    if @hover_glyph?
      @listenTo(@mget('data_source'), 'inspect', @request_render)

    # TODO (bev) This is a quick change that  allows the plot to be
    # update/re-rendered when properties change on the JS side. It would
    # be better to make this more fine grained in terms of setting visuals
    # and also could potentially be improved by making proper models out
    # of "Spec" properties. See https://github.com/bokeh/bokeh/pull/2684
    @listenTo(@mget('glyph'), 'propchange', () ->
        @glyph.set_visuals(@mget('data_source'))
        @request_render()
    )

  have_selection_glyphs: () -> @selection_glyph? && @nonselection_glyph?

  # TODO (bev) arg is a quick-fix to allow some hinting for things like
  # partial data updates (especially useful on expensive set_data calls
  # for image, e.g.)
  set_data: (request_render=true, arg) ->
    t0 = Date.now()
    source = @mget('data_source')

    @glyph.set_data(source, arg)

    @glyph.set_visuals(source)
    @decimated_glyph.set_visuals(source)
    if @have_selection_glyphs()
      @selection_glyph.set_visuals(source)
      @nonselection_glyph.set_visuals(source)
    if @hover_glyph?
      @hover_glyph.set_visuals(source)

    length = source.get_length()
    length = 1 if not length?
    @all_indices = [0...length]

    lod_factor = @plot_model.get('lod_factor')
    @decimated = []
    for i in [0...Math.floor(@all_indices.length/lod_factor)]
      @decimated.push(@all_indices[i*lod_factor])

    dt = Date.now() - t0
    logger.debug("#{@glyph.model.type} GlyphRenderer (#{@model.id}): set_data finished in #{dt}ms")

    @set_data_timestamp = Date.now()

    if request_render
      @request_render()

  render: () ->
    t0 = Date.now()

    glsupport = @glyph.glglyph

    tmap = Date.now()
    @glyph.map_data()
    dtmap = Date.now() - t0

    tmask = Date.now()
    if glsupport
      indices = @all_indices  # WebGL can do the clipping much more efficiently
    else
      indices = @glyph._mask_data(@all_indices)
    dtmask = Date.now() - tmask

    ctx = @plot_view.canvas_view.ctx
    ctx.save()

    selected = @mget('data_source').get('selected')
    if !selected or selected.length == 0
      selected = []
    else
      if selected['0d'].glyph
        selected = indices
      else if selected['1d'].indices.length > 0
        selected = selected['1d'].indices
      else if selected['2d'].indices.length > 0
        selected = selected['2d'].indices
      else
        selected = []

    inspected = @mget('data_source').get('inspected')
    if !inspected or inspected.length == 0
      inspected = []
    else
      if inspected['0d'].glyph
        inspected = indices
      else if inspected['1d'].indices.length > 0
        inspected = inspected['1d'].indices
      else if inspected['2d'].indices.length > 0
        inspected = inspected['2d'].indices
      else
        inspected = []

    lod_threshold = @plot_model.get('lod_threshold')
    if @plot_view.interactive and !glsupport and lod_threshold? and @all_indices.length > lod_threshold
      # Render decimated during interaction if too many elements and not using GL
      indices = @decimated
      glyph = @decimated_glyph
      nonselection_glyph = @decimated_glyph
      selection_glyph = @selection_glyph
    else
      glyph = @glyph
      nonselection_glyph = @nonselection_glyph
      selection_glyph = @selection_glyph

    if @hover_glyph? and inspected.length
      indices = _.without.bind(null, indices).apply(null, inspected)

    if not (selected.length and @have_selection_glyphs())
        trender = Date.now()
        glyph.render(ctx, indices, @glyph)
        if @hover_glyph and inspected.length
          @hover_glyph.render(ctx, inspected, @glyph)
        dtrender = Date.now() - trender

    else
      # reset the selection mask
      tselect = Date.now()
      selected_mask = {}
      for i in selected
        selected_mask[i] = true

      # intersect/different selection with render mask
      selected = new Array()
      nonselected = new Array()
      for i in indices
        if selected_mask[i]?
          selected.push(i)
        else
          nonselected.push(i)
      dtselect = Date.now() - tselect

      trender = Date.now()
      nonselection_glyph.render(ctx, nonselected, @glyph)
      selection_glyph.render(ctx, selected, @glyph)
      if @hover_glyph?
        @hover_glyph.render(ctx, inspected, @glyph)
      dtrender = Date.now() - trender

    @last_dtrender = dtrender

    dttot = Date.now() - t0
    logger.debug("#{@glyph.model.type} GlyphRenderer (#{@model.id}): render finished in #{dttot}ms")
    logger.trace(" - map_data finished in       : #{dtmap}ms")
    if dtmask?
      logger.trace(" - mask_data finished in      : #{dtmask}ms")
    if dtselect?
      logger.trace(" - selection mask finished in : #{dtselect}ms")
    logger.trace(" - glyph renders finished in  : #{dtrender}ms")

    ctx.restore()

  map_to_screen: (x, y) ->
    @plot_view.map_to_screen(x, y, @mget("x_range_name"), @mget("y_range_name"))

  draw_legend: (ctx, x0, x1, y0, y1) ->
    @glyph.draw_legend(ctx, x0, x1, y0, y1)

  hit_test: (geometry) ->
    @glyph.hit_test(geometry)

class GlyphRenderer extends Renderer
  default_view: GlyphRendererView
  type: 'GlyphRenderer'

  selection_defaults: {}
  decimated_defaults: {fill_alpha: 0.3, line_alpha: 0.3, fill_color: "grey", line_color: "grey"}
  nonselection_defaults: {fill_alpha: 0.2, line_alpha: 0.2}

  defaults: ->
    return _.extend {}, super(), {
      x_range_name: "default"
      y_range_name: "default"
      data_source: null
      level: 'glyph'
      glyph: null
      hover_glyph: null
      nonselection_glyph: null
      selection_glyph: null
    }

module.exports =
  Model: GlyphRenderer
  View: GlyphRendererView
