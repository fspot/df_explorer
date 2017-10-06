$(function() {
  if (!EVALEX_TRUSTED) {
    initPinBox();
  }

  /**
   * if we are in console mode, show the console.
   */
  if (CONSOLE_MODE && EVALEX) {
    openShell(null, $('div.console div.inner').empty(), 0);
  }

  $('div.traceback div.frame').each(function() {
    var
      target = $('pre', this),
      consoleNode = null,
      frameID = this.id.substring(6);

    target.click(function() {
      $(this).parent().toggleClass('expanded');
    });

    /**
     * Add an interactive console to the frames
     */
    if (EVALEX && target.is('.current')) {
      $('<img src="?__debugger__=yes&cmd=resource&f=console.png">')
        .attr('title', 'Open an interactive python shell in this frame')
        .click(function() {
          consoleNode = openShell(consoleNode, target, frameID);
          return false;
        })
        .prependTo(target);
    }
  });

  /**
   * toggle traceback types on click.
   */
  $('h2.traceback').click(function() {
    $(this).next().slideToggle('fast');
    $('div.plain').slideToggle('fast');
  }).css('cursor', 'pointer');
  $('div.plain').hide();

  /**
   * Add extra info (this is here so that only users with JavaScript
   * enabled see it.)
   */
  $('span.nojavascript')
    .removeClass('nojavascript')
    .html((!EVALEX ? '' :
          '<p>You can execute arbitrary Python code in the stack frames and ' +
          'there are some extra helpers available for introspection:' +
          '<ul><li><code>dump()</code> shows all variables in the frame' +
          '<li><code>dump(obj)</code> dumps all that\'s known about the object' +
          '<li><code>clear</code> clears the previous commands</ul>'
    ));

  /**
   * Add the pastebin feature
   */
  $('div.plain form')
    .submit(function() {
      var label = $('input[type="submit"]', this);
      var old_val = label.val();
      label.val('submitting...');
      $.ajax({
        dataType:     'json',
        url:          document.location.pathname,
        data:         {__debugger__: 'yes', tb: TRACEBACK, cmd: 'paste',
                       s: SECRET},
        success:      function(data) {
          $('div.plain span.pastemessage')
            .removeClass('pastemessage')
            .text('Paste created: ')
            .append($('<a>#' + data.id + '</a>').attr('href', data.url));
        },
        error:        function() {
          alert('Error: Could not submit paste.  No network connection?');
          label.val(old_val);
        }
      });
      return false;
    });

  // if we have javascript we submit by ajax anyways, so no need for the
  // not scaling textarea.
  var plainTraceback = $('div.plain textarea');
  plainTraceback.replaceWith($('<pre>').text(plainTraceback.text()));
});

function initPinBox() {
  $('.pin-prompt form').submit(function(evt) {
    evt.preventDefault();
    var pin = this.pin.value;
    var btn = this.btn;
    btn.disabled = true;
    $.ajax({
      dataType: 'json',
      url: document.location.pathname,
      data: {__debugger__: 'yes', cmd: 'pinauth', pin: pin,
             s: SECRET},
      success: function(data) {
        btn.disabled = false;
        if (data.auth) {
          EVALEX_TRUSTED = true;
          $('.pin-prompt').fadeOut();
        } else {
          if (data.exhausted) {
            alert('Error: too many attempts.  Restart server to retry.');
          } else {
            alert('Error: incorrect pin');
          }
        }
        console.log(data);
      },
      error: function() {
        btn.disabled = false;
        alert('Error: Could not verify PIN.  Network error?');
      }
    });
  });
}

function promptForPin() {
  if (!EVALEX_TRUSTED) {
    $.ajax({
      url: document.location.pathname,
      data: {__debugger__: 'yes', cmd: 'printpin', s: SECRET}
    });
    $('.pin-prompt').fadeIn(function() {
      $('.pin-prompt input[name="pin"]').focus();
    });
  }
}


/**
 * Helper function for shell initialization
 */
function openShell(consoleNode, target, frameID) {
  promptForPin();
  if (consoleNode)
    return consoleNode.slideToggle('fast');
  consoleNode = $('<pre class="console">')
    .appendTo(target.parent())
    .hide()
  var historyPos = 0, history = [''];
  var output = $('<div class="output">[console ready]</div>')
    .appendTo(consoleNode);
  var form = $('<form><div id="prompt">&gt;&gt;&gt;</div></form>')
    .submit(function() {
      var cmd = command.val();
      $.get('', {
          __debugger__: 'yes', cmd: cmd, frm: frameID, s: SECRET}, function(data) {
        var tmp = $('<div>').html(data);
        $('span.extended', tmp).each(function() {
          var hidden = $(this).wrap('<span>').hide();
          hidden
            .parent()
            .append($('<a href="#" class="toggle">&nbsp;&nbsp;</a>')
              .click(function() {
                hidden.toggle();
                $(this).toggleClass('open')
                return false;
              }));
        });
        output.append(tmp);
        command.focus();
        consoleNode.scrollTop(consoleNode.get(0).scrollHeight);
        var old = history.pop();
        history.push(cmd);
        if (typeof old != 'undefined')
          history.push(old);
        historyPos = history.length - 1;
      });
      command.val('');
      return false;
    }).
    appendTo(consoleNode);

  var MULTILINE_CHARS = ['{', '(', '[', ':', ',', '\\'];

  var command = $('<textarea rows="1" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">')
    .appendTo(form)
    .keypress(function(e) {
      if (e.charCode == 100 && e.ctrlKey) {
        alert("yay");
        output.text('--- screen cleared ---');
        return false;
      } else if (e.key === "Enter") {
        var do_submit = false;
        if (e.ctrlKey)
          do_submit = true;
        else {
          var last_char = command.val()[command.val().length - 1];
          if (MULTILINE_CHARS.indexOf(last_char) === -1)
            do_submit = true;
          if (command.val().indexOf('\n') !== -1)
            do_submit = false;
          if (command.val().trim() === "")
            do_submit = false;
        }

        if (command.val().trim() === 'clear') {
          do_submit = false;
          output.text('--- screen cleared ---');
          command.val("");
          autosize.update(command);
          return false;
        }

        if (do_submit) {
          form.submit();
          autosize.update(command);
          return false;
        }
      } else if (e.charCode == 0 && (e.keyCode == 38 || e.keyCode == 40)) {
        if (e.keyCode == 38 && historyPos > 0)
          historyPos--;
        else if (e.keyCode == 40 && historyPos < history.length)
          historyPos++;
        command.val(history[historyPos]);
        return false;
      }
    });

  return consoleNode.slideDown('fast', function() {
    command.focus();
  });
}

/*!
  Autosize 4.0.0
  license: MIT
  http://www.jacklmoore.com/autosize
*/
(function (global, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['exports', 'module'], factory);
  } else if (typeof exports !== 'undefined' && typeof module !== 'undefined') {
    factory(exports, module);
  } else {
    var mod = {
      exports: {}
    };
    factory(mod.exports, mod);
    global.autosize = mod.exports;
  }
})(this, function (exports, module) {
  'use strict';

  var map = typeof Map === "function" ? new Map() : (function () {
    var keys = [];
    var values = [];

    return {
      has: function has(key) {
        return keys.indexOf(key) > -1;
      },
      get: function get(key) {
        return values[keys.indexOf(key)];
      },
      set: function set(key, value) {
        if (keys.indexOf(key) === -1) {
          keys.push(key);
          values.push(value);
        }
      },
      'delete': function _delete(key) {
        var index = keys.indexOf(key);
        if (index > -1) {
          keys.splice(index, 1);
          values.splice(index, 1);
        }
      }
    };
  })();

  var createEvent = function createEvent(name) {
    return new Event(name, { bubbles: true });
  };
  try {
    new Event('test');
  } catch (e) {
    // IE does not support `new Event()`
    createEvent = function (name) {
      var evt = document.createEvent('Event');
      evt.initEvent(name, true, false);
      return evt;
    };
  }

  function assign(ta) {
    if (!ta || !ta.nodeName || ta.nodeName !== 'TEXTAREA' || map.has(ta)) return;

    var heightOffset = null;
    var clientWidth = ta.clientWidth;
    var cachedHeight = null;

    function init() {
      var style = window.getComputedStyle(ta, null);

      if (style.resize === 'vertical') {
        ta.style.resize = 'none';
      } else if (style.resize === 'both') {
        ta.style.resize = 'horizontal';
      }

      if (style.boxSizing === 'content-box') {
        heightOffset = -(parseFloat(style.paddingTop) + parseFloat(style.paddingBottom));
      } else {
        heightOffset = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
      }
      // Fix when a textarea is not on document body and heightOffset is Not a Number
      if (isNaN(heightOffset)) {
        heightOffset = 0;
      }

      update();
    }

    function changeOverflow(value) {
      {
        // Chrome/Safari-specific fix:
        // When the textarea y-overflow is hidden, Chrome/Safari do not reflow the text to account for the space
        // made available by removing the scrollbar. The following forces the necessary text reflow.
        var width = ta.style.width;
        ta.style.width = '0px';
        // Force reflow:
        /* jshint ignore:start */
        ta.offsetWidth;
        /* jshint ignore:end */
        ta.style.width = width;
      }

      ta.style.overflowY = value;
    }

    function getParentOverflows(el) {
      var arr = [];

      while (el && el.parentNode && el.parentNode instanceof Element) {
        if (el.parentNode.scrollTop) {
          arr.push({
            node: el.parentNode,
            scrollTop: el.parentNode.scrollTop
          });
        }
        el = el.parentNode;
      }

      return arr;
    }

    function resize() {
      var originalHeight = ta.style.height;
      var overflows = getParentOverflows(ta);
      var docTop = document.documentElement && document.documentElement.scrollTop; // Needed for Mobile IE (ticket #240)

      ta.style.height = '';

      var endHeight = ta.scrollHeight + heightOffset;

      if (ta.scrollHeight === 0) {
        // If the scrollHeight is 0, then the element probably has display:none or is detached from the DOM.
        ta.style.height = originalHeight;
        return;
      }

      ta.style.height = endHeight + 'px';

      // used to check if an update is actually necessary on window.resize
      clientWidth = ta.clientWidth;

      // prevents scroll-position jumping
      overflows.forEach(function (el) {
        el.node.scrollTop = el.scrollTop;
      });

      if (docTop) {
        document.documentElement.scrollTop = docTop;
      }
    }

    function update() {
      resize();

      var styleHeight = Math.round(parseFloat(ta.style.height));
      var computed = window.getComputedStyle(ta, null);

      // Using offsetHeight as a replacement for computed.height in IE, because IE does not account use of border-box
      var actualHeight = computed.boxSizing === 'content-box' ? Math.round(parseFloat(computed.height)) : ta.offsetHeight;

      // The actual height not matching the style height (set via the resize method) indicates that
      // the max-height has been exceeded, in which case the overflow should be allowed.
      if (actualHeight !== styleHeight) {
        if (computed.overflowY === 'hidden') {
          changeOverflow('scroll');
          resize();
          actualHeight = computed.boxSizing === 'content-box' ? Math.round(parseFloat(window.getComputedStyle(ta, null).height)) : ta.offsetHeight;
        }
      } else {
        // Normally keep overflow set to hidden, to avoid flash of scrollbar as the textarea expands.
        if (computed.overflowY !== 'hidden') {
          changeOverflow('hidden');
          resize();
          actualHeight = computed.boxSizing === 'content-box' ? Math.round(parseFloat(window.getComputedStyle(ta, null).height)) : ta.offsetHeight;
        }
      }

      if (cachedHeight !== actualHeight) {
        cachedHeight = actualHeight;
        var evt = createEvent('autosize:resized');
        try {
          ta.dispatchEvent(evt);
        } catch (err) {
          // Firefox will throw an error on dispatchEvent for a detached element
          // https://bugzilla.mozilla.org/show_bug.cgi?id=889376
        }
      }
    }

    var pageResize = function pageResize() {
      if (ta.clientWidth !== clientWidth) {
        update();
      }
    };

    var destroy = (function (style) {
      window.removeEventListener('resize', pageResize, false);
      ta.removeEventListener('input', update, false);
      ta.removeEventListener('keyup', update, false);
      ta.removeEventListener('autosize:destroy', destroy, false);
      ta.removeEventListener('autosize:update', update, false);

      Object.keys(style).forEach(function (key) {
        ta.style[key] = style[key];
      });

      map['delete'](ta);
    }).bind(ta, {
      height: ta.style.height,
      resize: ta.style.resize,
      overflowY: ta.style.overflowY,
      overflowX: ta.style.overflowX,
      wordWrap: ta.style.wordWrap
    });

    ta.addEventListener('autosize:destroy', destroy, false);

    // IE9 does not fire onpropertychange or oninput for deletions,
    // so binding to onkeyup to catch most of those events.
    // There is no way that I know of to detect something like 'cut' in IE9.
    if ('onpropertychange' in ta && 'oninput' in ta) {
      ta.addEventListener('keyup', update, false);
    }

    window.addEventListener('resize', pageResize, false);
    ta.addEventListener('input', update, false);
    ta.addEventListener('autosize:update', update, false);
    ta.style.overflowX = 'hidden';
    ta.style.wordWrap = 'break-word';

    map.set(ta, {
      destroy: destroy,
      update: update
    });

    init();
  }

  function destroy(ta) {
    var methods = map.get(ta);
    if (methods) {
      methods.destroy();
    }
  }

  function update(ta) {
    var methods = map.get(ta);
    if (methods) {
      methods.update();
    }
  }

  var autosize = null;

  // Do nothing in Node.js environment and IE8 (or lower)
  if (typeof window === 'undefined' || typeof window.getComputedStyle !== 'function') {
    autosize = function (el) {
      return el;
    };
    autosize.destroy = function (el) {
      return el;
    };
    autosize.update = function (el) {
      return el;
    };
  } else {
    autosize = function (el, options) {
      if (el) {
        Array.prototype.forEach.call(el.length ? el : [el], function (x) {
          return assign(x, options);
        });
      }
      return el;
    };
    autosize.destroy = function (el) {
      if (el) {
        Array.prototype.forEach.call(el.length ? el : [el], destroy);
      }
      return el;
    };
    autosize.update = function (el) {
      if (el) {
        Array.prototype.forEach.call(el.length ? el : [el], update);
      }
      return el;
    };
  }

  module.exports = autosize;
});

$(function() {
    $("div > pre.line.current > img").click();
    autosize(document.querySelectorAll('textarea'));
});
