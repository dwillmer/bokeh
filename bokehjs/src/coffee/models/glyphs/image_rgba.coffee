_ = require "underscore"
Glyph = require "./glyph"

class ImageRGBAView extends Glyph.View

  _index_data: () ->
    @_xy_index()

  # TODO (bev) to improve. Currently, if only one image has changed, can
  # pass index as "arg" to prevent full re-preocessing (useful for streaming)
  _set_data: (source, arg) ->
    if not @image_data? or @image_data.length != @image.length
      @image_data = new Array(@image.length)

    if not @width? or @width.length != @image.length
      @width = new Array(@image.length)

    if not @height? or @height.length != @image.length
      @height = new Array(@image.length)

    for i in [0...@image.length]
      if arg?
        if i != arg
          continue
      if @rows?
        @height[i] = @rows[i]
        @width[i] = @cols[i]
      else
        @height[i] = @image[i].length
        @width[i] = @image[i][0].length
      canvas = document.createElement('canvas')
      canvas.width = @width[i]
      canvas.height = @height[i]
      ctx = canvas.getContext('2d')
      image_data = ctx.getImageData(0, 0, @width[i], @height[i])
      if @rows?
        image_data.data.set(new Uint8ClampedArray(@image[i]))
      else
        flat = _.flatten(@image[i])
        buf = new ArrayBuffer(flat.length * 4)
        color = new Uint32Array(buf)
        for j in [0...flat.length]
          color[j] = flat[j]
        buf8 = new Uint8ClampedArray(buf)
        image_data.data.set(buf8)
      ctx.putImageData(image_data, 0, 0)
      @image_data[i] = canvas

      @max_dw = 0
      if @dw.units == "data"
        @max_dw = _.max(@dw)
      @max_dh = 0
      if @dh.units == "data"
        @max_dh = _.max(@dh)

  _map_data: () ->
    @sw = @sdist(@renderer.xmapper, @x, @dw, 'edge', @mget('dilate'))
    @sh = @sdist(@renderer.ymapper, @y, @dh, 'edge', @mget('dilate'))

  _render: (ctx, indices, {image_data, sx, sy, sw, sh}) ->
    old_smoothing = ctx.getImageSmoothingEnabled()
    ctx.setImageSmoothingEnabled(false)

    for i in indices

      if isNaN(sx[i]+sy[i]+sw[i]+sh[i])
        continue

      y_offset = sy[i]

      ctx.translate(0, y_offset)
      ctx.scale(1, -1)
      ctx.translate(0, -y_offset)
      ctx.drawImage(image_data[i], sx[i]|0, sy[i]|0, sw[i], sh[i])
      ctx.translate(0, y_offset)
      ctx.scale(1, -1)
      ctx.translate(0, -y_offset)

    ctx.setImageSmoothingEnabled(old_smoothing)

  bounds: () ->
    bb = @index.data.bbox
    return [
      [bb[0], bb[2]+@max_dw],
      [bb[1], bb[3]+@max_dh]
    ]

class ImageRGBA extends Glyph.Model
  default_view: ImageRGBAView
  type: 'ImageRGBA'
  visuals: []
  distances: ['dw', 'dh']
  fields: ['image:array', '?rows', '?cols']

  defaults: ->
    return _.extend {}, super(), {
      dilate: false
      rows: null
      cols: null
    }

module.exports =
  Model: ImageRGBA
  View: ImageRGBAView
