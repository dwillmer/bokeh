#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2015, Continuum Analytics, Inc. All rights reserved.
#
# Powered by the Bokeh Development Team.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------
''' Functions for configuring Bokeh output.

'''

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
from __future__ import absolute_import

# Stdlib imports
import logging
logger = logging.getLogger(__name__)

import io
import itertools
import json
import os
import warnings

# Third-party imports

# Bokeh imports
from .core.state import State
from .document import Document
from .embed import notebook_div, standalone_html_page_for_models, autoload_server
from .models import Component
from .models.plots import GridPlot
from .models.layouts import HBox, VBox, VBoxForm
from .model import _ModelInDocument
from .util.notebook import load_notebook, publish_display_data, get_comms
from .util.string import decode_utf8
from .util.serialization import make_id
import bokeh.util.browser as browserlib # full import needed for test mocking to work
from .client import DEFAULT_SESSION_ID, push_session, show_session

#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------

_new_param = {'tab': 2, 'window': 1}

_state = State()

#-----------------------------------------------------------------------------
# Local utilities
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

class _CommsHandle(object):

    _json = {}

    def __init__(self, comms, doc, json):
        self._cellno = None
        try:
            from IPython import get_ipython
            ip = get_ipython()
            hm = ip.history_manager
            p_prompt = list(hm.get_tail(1, include_latest=True))[0][1]
            self._cellno = p_prompt
        except Exception as e:
            logger.debug("Could not get Notebook cell number, reason: %s", e)

        self._comms = comms
        self._doc = doc
        self._json[doc] = json

    def _repr_html_(self):
        if self._cellno is not None:
            return "<p><code>&lt;Bokeh Notebook handle for <strong>In[%s]</strong>&gt;</code></p>" % str(self._cellno)
        else:
            return "<p><code>&lt;Bokeh Notebook handle&gt;</code></p>"

    @property
    def comms(self):
        return self._comms

    @property
    def doc(self):
        return self._doc

    @property
    def json(self):
        return self._json[self._doc]

    def update(self, doc, json):
        self._doc = doc
        self._json[doc] = json

def output_file(filename, title="Bokeh Plot", autosave=False, mode="cdn", root_dir=None):
    '''Configure the default output state to generate output saved
    to a file when :func:`show` is called.

    Does not change the current Document from curdoc(). File,
    server, and notebook output may be active at the same time, so
    this does not clear the effects of output_server() or
    output_notebook().

    Args:
        filename (str) : a filename for saving the HTML document

        title (str, optional) : a title for the HTML document (default: "Bokeh Plot")

        autosave (bool, optional) : whether to automatically save (default: False)
            If True, then Bokeh plotting APIs may opt to automatically
            save the file more frequently (e.g., after any plotting
            command). If False, then the file is only saved upon calling
            :func:`show` or :func:`save`.

        mode (str, optional) : how to include BokehJS (default: ``'inline'``)
            One of: ``'inline'``, ``'cdn'``, ``'relative(-dev)'`` or
            ``'absolute(-dev)'``. See :class:`bokeh.resources.Resources` for more details.

        root_dir (str, optional) : root directory to use for 'absolute' resources. (default: None)
            This value is ignored for other resource types, e.g. ``INLINE`` or
            ``CDN``.

    Returns:
        None

    .. note::
        Generally, this should be called at the beginning of an interactive
        session or the top of a script.

    .. warning::
        This output file will be overwritten on every save, e.g., each time
        show() or save() is invoked, or any time a Bokeh plotting API
        causes a save, if ``autosave`` is True.

    '''
    _state.output_file(
        filename,
        title=title,
        autosave=autosave,
        mode=mode,
        root_dir=root_dir
    )

def output_notebook(resources=None, verbose=False, hide_banner=False):
    ''' Configure the default output state to generate output in
    Jupyter/IPython notebook cells when :func:`show` is called.

    If output_server() has also been called, the notebook cells
    are loaded from the configured server; otherwise, Bokeh pushes
    HTML to the notebook directly.

    Args:
        resources (Resource, optional) :
            How and where to load BokehJS from (default: INLINE)

        verbose (bool, optional) :
            whether to display detailed BokehJS banner (default: False)

        hide_banner (bool, optional):
            whether to hide the Bokeh banner (default: False)

    Returns:
        None

    .. note::
        Generally, this should be called at the beginning of an interactive
        session or the top of a script.

    '''
    load_notebook(resources, verbose, hide_banner)
    _state.output_notebook()

# usually we default session_id to "generate a random one" but
# here we default to a hardcoded one. This is to support local
# usage e.g. with a notebook.
def output_server(session_id=DEFAULT_SESSION_ID, url="default", app_path="/", autopush=False):
    """ Configure the default output state to push its document to a
    session on a Bokeh server.

    Sessions are in-memory and not persisted to disk; in a typical
    production deployment, you would have a fresh session ID for each
    browser tab. If different users share the same session ID, it will
    create security and scalability problems.

    ``output_server()`` defaults to always using the
    ``session_id`` ``"default"``, which is useful for running
    local demos or notebooks. However, if you are creating
    production sessions, you'll need to set ``session_id`` to None
    (to generate a fresh ID) or to a session ID generated elsewhere.

    File, server, and notebook output may be active at the same
    time, so output_server() does not clear the effects of
    output_file() or output_notebook(). output_server() changes
    the behavior of output_notebook(), so the notebook will load
    output cells from the server rather than receiving them as
    inline HTML.

    Args:
        session_id (str, optional) : Name of session to push on Bokeh server (default: "default")
            Any existing session with the same name will be overwritten.

        url (str, optional) : base URL of the Bokeh server (default: "default")
            If "default" use the default localhost URL.

        app_path (str, optional) : relative path of the app on the Bokeh server (default: "/")

        autopush (bool, optional) : whether to automatically push (default: False)
            If True, then Bokeh plotting APIs may opt to automatically
            push the document more frequently (e.g., after any plotting
            command). If False, then the document is only pushed upon calling
            :func:`show` or :func:`push`.

    Returns:
        None

    .. warning::
        Calling this function will replace any existing server-side document in the named session.

    """

    _state.output_server(session_id=session_id, url=url, app_path=app_path, autopush=autopush)

def set_curdoc(doc):
    '''Configure the current document (returned by curdoc()).

    This is the document we will save or push according to
    output_file(), output_server(), etc. configuration.

    Args:
        doc (Document) : Document we will output.

    Returns:
        None

    .. note::
        Generally, this should be called at the beginning of an interactive
        session or the top of a script.

    .. warning::
        Calling this function will replace any existing document.

    '''
    _state.document = doc

def curdoc():
    ''' Return the document for the current default state.

    Returns:
        doc : the current default document object.

    '''
    return _state.document

def curstate():
    ''' Return the current State object

    Returns:
      state : the current default State object
    '''
    return _state

def show(obj, browser=None, new="tab"):
    ''' Immediately display a plot object.

    In an IPython/Jupyter notebook, the output is displayed in an output
    cell. Otherwise, a browser window or tab is autoraised to display the
    plot object.

    If both a server session and notebook output have been configured on
    the default output state then the notebook output will be generated to
    load the plot from that server session.

    Args:
        obj (Component object) : a plot object to display

        browser (str, optional) : browser to show with (default: None)
            For systems that support it, the **browser** argument allows
            specifying which browser to display in, e.g. "safari", "firefox",
            "opera", "windows-default" (see the ``webbrowser`` module
            documentation in the standard lib for more details).

        new (str, optional) : new file output mode (default: "tab")
            For file-based output, opens or raises the browser window
            showing the current output file.  If **new** is 'tab', then
            opens a new tab. If **new** is 'window', then opens a new window.

    Returns:
        when in a a jupyter notebook (with ``output_notebook`` enabled), returns
        a handle that can be used by ``push_notebook``, None otherwise.

    .. note::
        The ``browser`` and ``new`` parameters are ignored when showing in
        an IPython/Jupyter notebook.

    '''
    return _show_with_state(obj, _state, browser, new)

def _show_with_state(obj, state, browser, new):
    controller = browserlib.get_browser_controller(browser=browser)

    comms_handle = None

    if state.notebook:
        comms_handle = _show_notebook_with_state(obj, state)

    elif state.server_enabled:
        _show_server_with_state(obj, state, new, controller)

    if state.file:
        _show_file_with_state(obj, state, new, controller)

    return comms_handle

def _show_file_with_state(obj, state, new, controller):
    save(obj, state=state)
    controller.open("file://" + os.path.abspath(state.file['filename']), new=_new_param[new])

def _show_notebook_with_state(obj, state):
    if state.server_enabled:
        push(state=state)
        snippet = autoload_server(obj, session_id=state.session_id_allowing_none, url=state.url, app_path=state.app_path)
        publish_display_data({'text/html': snippet})
    else:
        comms_target = make_id()
        publish_display_data({'text/html': notebook_div(obj, comms_target)})
        handle = _CommsHandle(get_comms(comms_target), state.document, state.document.to_json())
        state.last_comms_handle = handle
        return handle

def _show_server_with_state(obj, state, new, controller):
    push(state=state)
    show_session(session_id=state.session_id_allowing_none, url=state.url, app_path=state.app_path,
                 new=new, controller=controller)

def save(obj, filename=None, resources=None, title=None, state=None, validate=True):
    ''' Save an HTML file with the data for the current document.

    Will fall back to the default output state (or an explicitly provided
    :class:`State` object) for ``filename``, ``resources``, or ``title`` if they
    are not provided.

    Args:
        obj (Document or model object) : a plot object to save

        filename (str, optional) : filename to save document under (default: None)
            If None, use the default state configuration, otherwise raise a
            ``RuntimeError``.

        resources (Resources, optional) : A Resources config to use (default: None)
            If None, use the default state configuration, if there is one.
            otherwise use ``resources.INLINE``.

        title (str, optional) : a title for the HTML document (default: None)
            If None, use the default state title value, if there is one.
            Otherwise, use "Bokeh Plot"

        validate (bool, optional) : True to check integrity of the models

    Returns:
        None

    Raises:
        RuntimeError

    '''
    if state is None:
        state = _state

    filename, resources, title = _get_save_args(state, filename, resources, title)

    _save_helper(obj, filename, resources, title, validate)

def _get_save_args(state, filename, resources, title):

    if filename is None and state.file:
        filename = state.file['filename']

    if resources is None and state.file:
        resources = state.file['resources']

    if title is None and state.file:
        title = state.file['title']

    if filename is None:
        raise RuntimeError("save() called but no filename was supplied and output_file(...) was never called, nothing saved")

    if resources is None:
        warnings.warn("save() called but no resources were supplied and output_file(...) was never called, defaulting to resources.CDN")
        from .resources import CDN
        resources = CDN

    if title is None:
        warnings.warn("save() called but no title was supplied and output_file(...) was never called, using default title 'Bokeh Plot'")
        title = "Bokeh Plot"

    return filename, resources, title

def _save_helper(obj, filename, resources, title, validate):
    with _ModelInDocument(obj):
        if isinstance(obj, Component):
            doc = obj.document
        elif isinstance(obj, Document):
            doc = obj
        else:
            raise RuntimeError("Unable to save object of type '%s'" % type(obj))

        if validate:
            doc.validate()

        html = standalone_html_page_for_models(obj, resources, title)

        with io.open(filename, "w", encoding="utf-8") as f:
            f.write(decode_utf8(html))

# this function exists mostly to be mocked in tests
def _push_to_server(session_id, url, app_path, document, io_loop):
    session = push_session(document, session_id=session_id, url=url, app_path=app_path, io_loop=io_loop)
    session.close()
    session.loop_until_closed()

def push(session_id=None, url=None, app_path=None, document=None, state=None, io_loop=None, validate=True):
    ''' Update the server with the data for the current document.

    Will fall back to the default output state (or an explicitly
    provided :class:`State` object) for ``session_id``, ``url``,
    ``app_path``, or ``document`` if they are not provided.

    Args:
        session_id (str, optional) : a Bokeh server session ID to push objects to

        url (str, optional) : a Bokeh server URL to push objects to

        app_path (str, optional) : Relative application path to push objects to

        document (Document, optional) : A :class:`bokeh.document.Document` to use

        state (State, optional) : A state to use for any output_server() configuration of session or url

        io_loop (tornado.ioloop.IOLoop, optional) : Tornado IOLoop to use for connecting to server

        validate (bool, optional) : True to check integrity of the document we are pushing

    Returns:
        None

    '''
    if state is None:
        state = _state

    if not session_id:
        session_id = state.session_id_allowing_none

    if not url:
        url = state.url

    if not app_path:
        app_path = state.app_path

    # State is supposed to ensure these are set
    assert session_id is not None
    assert url is not None
    assert app_path is not None

    if not document:
        document = state.document

    if not document:
        warnings.warn("No document to push")

    if validate:
        document.validate()

    _push_to_server(session_id=session_id, url=url, app_path=app_path,
                    document=document, io_loop=io_loop)

def push_notebook(document=None, state=None, handle=None):
    ''' Update the last-shown plot in a Jupyter notebook with the new data
    or property values.

    Args:

        document (Document, optional) :
            A :class:`~bokeh.document.Document` to push from. If None,
            uses ``curdoc()``.

        state (State, optional) :
            A Bokeh State object

    Returns:
        None

    Examples:

        Typical usage is typically similar to this:

        .. code-block:: python

            from bokeh.io import push_notebook

            # code to create a plot

            show(plot)

            plot.title = "New Title"

            # This will cause the title to update
            push_notebook()

    '''
    if state is None:
        state = _state

    if state.server_enabled:
        raise RuntimeError("output_server() has been called, use push() to push to server")

    if not document:
        document = state.document

    if not document:
        warnings.warn("No document to push")
        return

    if handle is None:
        handle = state.last_comms_handle

    if not handle:
        warnings.warn("Cannot find a last shown plot to update. Call output_notebook() and show() before push_notebook()")
        return

    to_json = document.to_json()
    if handle.doc is not document:
        msg = dict(doc=to_json)
    else:
        msg = Document._compute_patch_between_json(handle.json, to_json)
    handle.comms.send(json.dumps(msg))
    handle.update(document, to_json)

def reset_output(state=None):
    ''' Clear the default state of all output modes.

    Returns:
        None

    '''
    _state.reset()

def _remove_roots(subplots):
    doc = _state.document
    for sub in subplots:
        if sub in doc.roots:
            doc.remove_root(sub)

def _push_or_save(obj):
    if _state.server_enabled and _state.autopush:
        push()
    if _state.file and _state.autosave:
        save(obj)

def gridplot(plot_arrangement, **kwargs):
    ''' Generate a plot that arranges several subplots into a grid.

    Args:
        plot_arrangement (nested list of Plots) : plots to arrange in a grid
        **kwargs: additional attributes to pass in to GridPlot() constructor

    .. note:: ``plot_arrangement`` can be nested, e.g [[p1, p2], [p3, p4]]

    Returns:
        grid_plot: a new :class:`GridPlot <bokeh.models.plots.GridPlot>`

    '''
    subplots = itertools.chain.from_iterable(plot_arrangement)
    _remove_roots(subplots)
    grid = GridPlot(children=plot_arrangement, **kwargs)
    curdoc().add_root(grid)
    _push_or_save(grid)
    return grid

def hplot(*children, **kwargs):
    ''' Generate a layout that arranges several subplots horizontally.

    '''
    _remove_roots(children)
    layout = HBox(children=list(children), **kwargs)
    curdoc().add_root(layout)
    _push_or_save(layout)
    return layout

def vplot(*children, **kwargs):
    ''' Generate a layout that arranges several subplots vertically.

    '''
    _remove_roots(children)
    layout = VBox(children=list(children), **kwargs)
    curdoc().add_root(layout)
    _push_or_save(layout)
    return layout

def vform(*children, **kwargs):
    ''' Generate a layout that arranges several subplots vertically.

    '''
    layout = VBoxForm(children=list(children), **kwargs)
    curdoc().add_root(layout)
    _push_or_save(layout)
    return layout
