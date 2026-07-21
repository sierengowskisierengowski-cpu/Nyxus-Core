"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// ../../node_modules/.pnpm/path-is-absolute@1.0.1/node_modules/path-is-absolute/index.js
var require_path_is_absolute = __commonJS({
  "../../node_modules/.pnpm/path-is-absolute@1.0.1/node_modules/path-is-absolute/index.js"(exports2, module2) {
    "use strict";
    function posix(path2) {
      return path2.charAt(0) === "/";
    }
    function win32(path2) {
      var splitDeviceRe = /^([a-zA-Z]:|[\\\/]{2}[^\\\/]+[\\\/]+[^\\\/]+)?([\\\/])?([\s\S]*?)$/;
      var result = splitDeviceRe.exec(path2);
      var device = result[1] || "";
      var isUnc = Boolean(device && device.charAt(1) !== ":");
      return Boolean(result[2] || isUnc);
    }
    module2.exports = process.platform === "win32" ? win32 : posix;
    module2.exports.posix = posix;
    module2.exports.win32 = win32;
  }
});

// ../../node_modules/.pnpm/winreg@1.2.4/node_modules/winreg/lib/registry.js
var require_registry = __commonJS({
  "../../node_modules/.pnpm/winreg@1.2.4/node_modules/winreg/lib/registry.js"(exports2, module2) {
    var util = require("util");
    var path2 = require("path");
    var spawn2 = require("child_process").spawn;
    var log2 = function() {
    };
    var HKLM = "HKLM";
    var HKCU = "HKCU";
    var HKCR = "HKCR";
    var HKU = "HKU";
    var HKCC = "HKCC";
    var HIVES = [HKLM, HKCU, HKCR, HKU, HKCC];
    var REG_SZ = "REG_SZ";
    var REG_MULTI_SZ = "REG_MULTI_SZ";
    var REG_EXPAND_SZ = "REG_EXPAND_SZ";
    var REG_DWORD = "REG_DWORD";
    var REG_QWORD = "REG_QWORD";
    var REG_BINARY = "REG_BINARY";
    var REG_NONE = "REG_NONE";
    var REG_TYPES = [REG_SZ, REG_MULTI_SZ, REG_EXPAND_SZ, REG_DWORD, REG_QWORD, REG_BINARY, REG_NONE];
    var DEFAULT_VALUE = "";
    var KEY_PATTERN = /(\\[a-zA-Z0-9_\s]+)*/;
    var PATH_PATTERN = /^(HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|HKEY_CLASSES_ROOT|HKEY_USERS|HKEY_CURRENT_CONFIG)(.*)$/;
    var ITEM_PATTERN = /^(.*)\s(REG_SZ|REG_MULTI_SZ|REG_EXPAND_SZ|REG_DWORD|REG_QWORD|REG_BINARY|REG_NONE)\s+([^\s].*)$/;
    function ProcessUncleanExitError(message, code) {
      if (!(this instanceof ProcessUncleanExitError))
        return new ProcessUncleanExitError(message, code);
      Error.captureStackTrace(this, ProcessUncleanExitError);
      this.__defineGetter__("name", function() {
        return ProcessUncleanExitError.name;
      });
      this.__defineGetter__("message", function() {
        return message;
      });
      this.__defineGetter__("code", function() {
        return code;
      });
    }
    util.inherits(ProcessUncleanExitError, Error);
    function captureOutput(child) {
      var output = { "stdout": "", "stderr": "" };
      child.stdout.on("data", function(data) {
        output["stdout"] += data.toString();
      });
      child.stderr.on("data", function(data) {
        output["stderr"] += data.toString();
      });
      return output;
    }
    function mkErrorMsg(registryCommand, code, output) {
      var stdout = output["stdout"].trim();
      var stderr = output["stderr"].trim();
      var msg = util.format("%s command exited with code %d:\n%s\n%s", registryCommand, code, stdout, stderr);
      return new ProcessUncleanExitError(msg, code);
    }
    function convertArchString(archString) {
      if (archString == "x64") {
        return "64";
      } else if (archString == "x86") {
        return "32";
      } else {
        throw new Error("illegal architecture: " + archString + " (use x86 or x64)");
      }
    }
    function pushArch(args, arch) {
      if (arch) {
        args.push("/reg:" + convertArchString(arch));
      }
    }
    function getRegExePath() {
      if (process.platform === "win32") {
        return path2.join(process.env.windir, "system32", "reg.exe");
      } else {
        return "REG";
      }
    }
    function RegistryItem(host, hive, key, name, type, value, arch) {
      if (!(this instanceof RegistryItem))
        return new RegistryItem(host, hive, key, name, type, value, arch);
      var _host = host, _hive = hive, _key = key, _name = name, _type = type, _value = value, _arch = arch;
      this.__defineGetter__("host", function() {
        return _host;
      });
      this.__defineGetter__("hive", function() {
        return _hive;
      });
      this.__defineGetter__("key", function() {
        return _key;
      });
      this.__defineGetter__("name", function() {
        return _name;
      });
      this.__defineGetter__("type", function() {
        return _type;
      });
      this.__defineGetter__("value", function() {
        return _value;
      });
      this.__defineGetter__("arch", function() {
        return _arch;
      });
    }
    util.inherits(RegistryItem, Object);
    function Registry(options) {
      if (!(this instanceof Registry))
        return new Registry(options);
      var _options = options || {}, _host = "" + (_options.host || ""), _hive = "" + (_options.hive || HKLM), _key = "" + (_options.key || ""), _arch = _options.arch || null;
      this.__defineGetter__("host", function() {
        return _host;
      });
      this.__defineGetter__("hive", function() {
        return _hive;
      });
      this.__defineGetter__("key", function() {
        return _key;
      });
      this.__defineGetter__("path", function() {
        return (_host.length == 0 ? "" : "\\\\" + _host + "\\") + _hive + _key;
      });
      this.__defineGetter__("arch", function() {
        return _arch;
      });
      this.__defineGetter__("parent", function() {
        var i = _key.lastIndexOf("\\");
        return new Registry({
          host: this.host,
          hive: this.hive,
          key: i == -1 ? "" : _key.substring(0, i),
          arch: this.arch
        });
      });
      if (HIVES.indexOf(_hive) == -1)
        throw new Error("illegal hive specified.");
      if (!KEY_PATTERN.test(_key))
        throw new Error("illegal key specified.");
      if (_arch && _arch != "x64" && _arch != "x86")
        throw new Error("illegal architecture specified (use x86 or x64)");
    }
    Registry.HKLM = HKLM;
    Registry.HKCU = HKCU;
    Registry.HKCR = HKCR;
    Registry.HKU = HKU;
    Registry.HKCC = HKCC;
    Registry.HIVES = HIVES;
    Registry.REG_SZ = REG_SZ;
    Registry.REG_MULTI_SZ = REG_MULTI_SZ;
    Registry.REG_EXPAND_SZ = REG_EXPAND_SZ;
    Registry.REG_DWORD = REG_DWORD;
    Registry.REG_QWORD = REG_QWORD;
    Registry.REG_BINARY = REG_BINARY;
    Registry.REG_NONE = REG_NONE;
    Registry.REG_TYPES = REG_TYPES;
    Registry.DEFAULT_VALUE = DEFAULT_VALUE;
    Registry.prototype.values = function values(cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = ["QUERY", this.path];
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), buffer = "", self = this, error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("QUERY", code, output), null);
        } else {
          var items = [], result = [], lines = buffer.split("\n"), lineNumber = 0;
          for (var i = 0, l = lines.length; i < l; i++) {
            var line = lines[i].trim();
            if (line.length > 0) {
              log2(line);
              if (lineNumber != 0) {
                items.push(line);
              }
              ++lineNumber;
            }
          }
          for (var i = 0, l = items.length; i < l; i++) {
            var match = ITEM_PATTERN.exec(items[i]), name, type, value;
            if (match) {
              name = match[1].trim();
              type = match[2].trim();
              value = match[3];
              result.push(new RegistryItem(self.host, self.hive, self.key, name, type, value, self.arch));
            }
          }
          cb(null, result);
        }
      });
      proc.stdout.on("data", function(data) {
        buffer += data.toString();
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.keys = function keys(cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = ["QUERY", this.path];
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), buffer = "", self = this, error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("QUERY", code, output), null);
        }
      });
      proc.stdout.on("data", function(data) {
        buffer += data.toString();
      });
      proc.stdout.on("end", function() {
        var items = [], result = [], lines = buffer.split("\n");
        for (var i = 0, l = lines.length; i < l; i++) {
          var line = lines[i].trim();
          if (line.length > 0) {
            log2(line);
            items.push(line);
          }
        }
        for (var i = 0, l = items.length; i < l; i++) {
          var match = PATH_PATTERN.exec(items[i]), hive, key;
          if (match) {
            hive = match[1];
            key = match[2];
            if (key && key !== self.key) {
              result.push(new Registry({
                host: self.host,
                hive: self.hive,
                key,
                arch: self.arch
              }));
            }
          }
        }
        cb(null, result);
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.get = function get(name, cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = ["QUERY", this.path];
      if (name == "")
        args.push("/ve");
      else
        args = args.concat(["/v", name]);
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), buffer = "", self = this, error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("QUERY", code, output), null);
        } else {
          var items = [], result = null, lines = buffer.split("\n"), lineNumber = 0;
          for (var i = 0, l = lines.length; i < l; i++) {
            var line = lines[i].trim();
            if (line.length > 0) {
              log2(line);
              if (lineNumber != 0) {
                items.push(line);
              }
              ++lineNumber;
            }
          }
          var item = items[items.length - 1] || "", match = ITEM_PATTERN.exec(item), name2, type, value;
          if (match) {
            name2 = match[1].trim();
            type = match[2].trim();
            value = match[3];
            result = new RegistryItem(self.host, self.hive, self.key, name2, type, value, self.arch);
          }
          cb(null, result);
        }
      });
      proc.stdout.on("data", function(data) {
        buffer += data.toString();
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.set = function set(name, type, value, cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      if (REG_TYPES.indexOf(type) == -1)
        throw Error("illegal type specified.");
      var args = ["ADD", this.path];
      if (name == "")
        args.push("/ve");
      else
        args = args.concat(["/v", name]);
      args = args.concat(["/t", type, "/d", value, "/f"]);
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("ADD", code, output, null));
        } else {
          cb(null);
        }
      });
      proc.stdout.on("data", function(data) {
        log2("" + data);
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.remove = function remove(name, cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = name ? ["DELETE", this.path, "/f", "/v", name] : ["DELETE", this.path, "/f", "/ve"];
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("DELETE", code, output), null);
        } else {
          cb(null);
        }
      });
      proc.stdout.on("data", function(data) {
        log2("" + data);
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.clear = function clear(cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = ["DELETE", this.path, "/f", "/va"];
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("DELETE", code, output), null);
        } else {
          cb(null);
        }
      });
      proc.stdout.on("data", function(data) {
        log2("" + data);
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.erase = Registry.prototype.clear;
    Registry.prototype.destroy = function destroy(cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = ["DELETE", this.path, "/f"];
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("DELETE", code, output), null);
        } else {
          cb(null);
        }
      });
      proc.stdout.on("data", function(data) {
        log2("" + data);
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.create = function create(cb) {
      if (typeof cb !== "function")
        throw new TypeError("must specify a callback");
      var args = ["ADD", this.path, "/f"];
      pushArch(args, this.arch);
      var proc = spawn2(getRegExePath(), args, {
        cwd: void 0,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      }), error = null;
      var output = captureOutput(proc);
      proc.on("close", function(code) {
        if (error) {
          return;
        } else if (code !== 0) {
          log2("process exited with code " + code);
          cb(mkErrorMsg("ADD", code, output), null);
        } else {
          cb(null);
        }
      });
      proc.stdout.on("data", function(data) {
        log2("" + data);
      });
      proc.on("error", function(err) {
        error = err;
        cb(err);
      });
      return this;
    };
    Registry.prototype.keyExists = function keyExists(cb) {
      this.values(function(err, items) {
        if (err) {
          if (err.code == 1) {
            return cb(null, false);
          }
          return cb(err);
        }
        cb(null, true);
      });
      return this;
    };
    Registry.prototype.valueExists = function valueExists(name, cb) {
      this.get(name, function(err, item) {
        if (err) {
          if (err.code == 1) {
            return cb(null, false);
          }
          return cb(err);
        }
        cb(null, true);
      });
      return this;
    };
    module2.exports = Registry;
  }
});

// ../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/AutoLaunchWindows.js
var require_AutoLaunchWindows = __commonJS({
  "../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/AutoLaunchWindows.js"(exports2, module2) {
    var Winreg;
    var fs2;
    var path2;
    var regKey;
    fs2 = require("fs");
    path2 = require("path");
    Winreg = require_registry();
    regKey = new Winreg({
      hive: Winreg.HKCU,
      key: "\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    });
    module2.exports = {
      /* Public */
      enable: function(arg) {
        var appName, appPath, isHiddenOnLaunch;
        appName = arg.appName, appPath = arg.appPath, isHiddenOnLaunch = arg.isHiddenOnLaunch;
        return new Promise(function(resolve, reject) {
          var args, pathToAutoLaunchedApp, ref, updateDotExe;
          pathToAutoLaunchedApp = appPath;
          args = "";
          updateDotExe = path2.join(path2.dirname(process.execPath), "..", "update.exe");
          if (((ref = process.versions) != null ? ref.electron : void 0) != null && fs2.existsSync(updateDotExe)) {
            pathToAutoLaunchedApp = updateDotExe;
            args = ' --processStart "' + path2.basename(process.execPath) + '"';
            if (isHiddenOnLaunch) {
              args += ' --process-start-args "--hidden"';
            }
          } else {
            if (isHiddenOnLaunch) {
              args += " --hidden";
            }
          }
          return regKey.set(appName, Winreg.REG_SZ, '"' + pathToAutoLaunchedApp + '"' + args, function(err) {
            if (err != null) {
              return reject(err);
            }
            return resolve();
          });
        });
      },
      disable: function(appName) {
        return new Promise(function(resolve, reject) {
          return regKey.remove(appName, function(err) {
            if (err != null) {
              if (err.message.indexOf("The system was unable to find the specified registry key or value") !== -1) {
                return resolve(false);
              }
              return reject(err);
            }
            return resolve();
          });
        });
      },
      isEnabled: function(appName) {
        return new Promise(function(resolve, reject) {
          return regKey.get(appName, function(err, item) {
            if (err != null) {
              return resolve(false);
            }
            return resolve(item != null);
          });
        });
      }
    };
  }
});

// ../../node_modules/.pnpm/applescript@1.0.0/node_modules/applescript/lib/applescript-parser.js
var require_applescript_parser = __commonJS({
  "../../node_modules/.pnpm/applescript@1.0.0/node_modules/applescript/lib/applescript-parser.js"(exports2) {
    exports2.parse = function(str) {
      if (str.length == 0) {
        return;
      }
      var rtn = parseFromFirstRemaining.call({
        value: str,
        index: 0
      });
      return rtn;
    };
    function parseFromFirstRemaining() {
      var cur = this.value[this.index];
      switch (cur) {
        case "{":
          return exports2.ArrayParser.call(this);
          break;
        case '"':
          return exports2.StringParser.call(this);
          break;
        case "a":
          if (this.value.substring(this.index, this.index + 5) == "alias") {
            return exports2.AliasParser.call(this);
          }
          break;
        case "\xAB":
          if (this.value.substring(this.index, this.index + 5) == "\xABdata") {
            return exports2.DataParser.call(this);
          }
          break;
      }
      if (!isNaN(cur)) {
        return exports2.NumberParser.call(this);
      }
      return exports2.UndefinedParser.call(this);
    }
    exports2.AliasParser = function() {
      this.index += 6;
      return "/Volumes/" + exports2.StringParser.call(this).replace(/:/g, "/");
    };
    exports2.ArrayParser = function() {
      var rtn = [], cur = this.value[++this.index];
      while (cur != "}") {
        rtn.push(parseFromFirstRemaining.call(this));
        if (this.value[this.index] == ",") this.index += 2;
        cur = this.value[this.index];
      }
      this.index++;
      return rtn;
    };
    exports2.DataParser = function() {
      var body = exports2.UndefinedParser.call(this);
      body = body.substring(6, body.length - 1);
      var type = body.substring(0, 4);
      body = body.substring(4, body.length);
      var buf = new Buffer(body.length / 2);
      var count = 0;
      for (var i = 0, l = body.length; i < l; i += 2) {
        buf[count++] = parseInt(body[i] + body[i + 1], 16);
      }
      buf.type = type;
      return buf;
    };
    exports2.NumberParser = function() {
      return Number(exports2.UndefinedParser.call(this));
    };
    exports2.StringParser = function(str) {
      var rtn = "", end = ++this.index, cur = this.value[end++];
      while (cur != '"') {
        if (cur == "\\") {
          rtn += this.value.substring(this.index, end - 1);
          this.index = end++;
        }
        cur = this.value[end++];
      }
      rtn += this.value.substring(this.index, end - 1);
      this.index = end;
      return rtn;
    };
    var END_OF_TOKEN = /}|,|\n/;
    exports2.UndefinedParser = function() {
      var end = this.index, cur = this.value[end++];
      while (!END_OF_TOKEN.test(cur)) {
        cur = this.value[end++];
      }
      var rtn = this.value.substring(this.index, end - 1);
      this.index = end - 1;
      return rtn;
    };
  }
});

// ../../node_modules/.pnpm/applescript@1.0.0/node_modules/applescript/lib/applescript.js
var require_applescript = __commonJS({
  "../../node_modules/.pnpm/applescript@1.0.0/node_modules/applescript/lib/applescript.js"(exports2) {
    var spawn2 = require("child_process").spawn;
    exports2.Parsers = require_applescript_parser();
    var parse = exports2.Parsers.parse;
    exports2.osascript = "osascript";
    exports2.execFile = function execFile(file, args, callback) {
      if (!Array.isArray(args)) {
        callback = args;
        args = [];
      }
      return runApplescript(file, args, callback);
    };
    exports2.execString = function execString(str, callback) {
      return runApplescript(str, callback);
    };
    function runApplescript(strOrPath, args, callback) {
      var isString = false;
      if (!Array.isArray(args)) {
        callback = args;
        args = [];
        isString = true;
      }
      args.push("-ss");
      if (!isString) {
        args.push(strOrPath);
      }
      var interpreter = spawn2(exports2.osascript, args);
      bufferBody(interpreter.stdout);
      bufferBody(interpreter.stderr);
      interpreter.on("exit", function(code) {
        var result = parse(interpreter.stdout.body);
        var err;
        if (code) {
          err = new Error(interpreter.stderr.body);
          err.appleScript = strOrPath;
          err.exitCode = code;
        }
        if (callback) {
          callback(err, result, interpreter.stderr.body);
        }
      });
      if (isString) {
        interpreter.stdin.write(strOrPath);
        interpreter.stdin.end();
      }
    }
    function bufferBody(stream) {
      stream.body = "";
      stream.setEncoding("utf8");
      stream.on("data", function(chunk) {
        stream.body += chunk;
      });
    }
  }
});

// ../../node_modules/.pnpm/untildify@3.0.3/node_modules/untildify/index.js
var require_untildify = __commonJS({
  "../../node_modules/.pnpm/untildify@3.0.3/node_modules/untildify/index.js"(exports2, module2) {
    "use strict";
    var home = require("os").homedir();
    module2.exports = (str) => {
      if (typeof str !== "string") {
        throw new TypeError(`Expected a string, got ${typeof str}`);
      }
      return home ? str.replace(/^~(?=$|\/|\\)/, home) : str;
    };
  }
});

// ../../node_modules/.pnpm/mkdirp@0.5.6/node_modules/mkdirp/index.js
var require_mkdirp = __commonJS({
  "../../node_modules/.pnpm/mkdirp@0.5.6/node_modules/mkdirp/index.js"(exports2, module2) {
    var path2 = require("path");
    var fs2 = require("fs");
    var _0777 = parseInt("0777", 8);
    module2.exports = mkdirP.mkdirp = mkdirP.mkdirP = mkdirP;
    function mkdirP(p, opts, f, made) {
      if (typeof opts === "function") {
        f = opts;
        opts = {};
      } else if (!opts || typeof opts !== "object") {
        opts = { mode: opts };
      }
      var mode = opts.mode;
      var xfs = opts.fs || fs2;
      if (mode === void 0) {
        mode = _0777;
      }
      if (!made) made = null;
      var cb = f || /* istanbul ignore next */
      function() {
      };
      p = path2.resolve(p);
      xfs.mkdir(p, mode, function(er) {
        if (!er) {
          made = made || p;
          return cb(null, made);
        }
        switch (er.code) {
          case "ENOENT":
            if (path2.dirname(p) === p) return cb(er);
            mkdirP(path2.dirname(p), opts, function(er2, made2) {
              if (er2) cb(er2, made2);
              else mkdirP(p, opts, cb, made2);
            });
            break;
          // In the case of any other error, just see if there's a dir
          // there already.  If so, then hooray!  If not, then something
          // is borked.
          default:
            xfs.stat(p, function(er2, stat) {
              if (er2 || !stat.isDirectory()) cb(er, made);
              else cb(null, made);
            });
            break;
        }
      });
    }
    mkdirP.sync = function sync(p, opts, made) {
      if (!opts || typeof opts !== "object") {
        opts = { mode: opts };
      }
      var mode = opts.mode;
      var xfs = opts.fs || fs2;
      if (mode === void 0) {
        mode = _0777;
      }
      if (!made) made = null;
      p = path2.resolve(p);
      try {
        xfs.mkdirSync(p, mode);
        made = made || p;
      } catch (err0) {
        switch (err0.code) {
          case "ENOENT":
            made = sync(path2.dirname(p), opts, made);
            sync(p, opts, made);
            break;
          // In the case of any other error, just see if there's a dir
          // there already.  If so, then hooray!  If not, then something
          // is borked.
          default:
            var stat;
            try {
              stat = xfs.statSync(p);
            } catch (err1) {
              throw err0;
            }
            if (!stat.isDirectory()) throw err0;
            break;
        }
      }
      return made;
    };
  }
});

// ../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/fileBasedUtilities.js
var require_fileBasedUtilities = __commonJS({
  "../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/fileBasedUtilities.js"(exports2, module2) {
    var fs2;
    var mkdirp;
    fs2 = require("fs");
    mkdirp = require_mkdirp();
    module2.exports = {
      /* Public */
      createFile: function(arg) {
        var data, directory, filePath;
        directory = arg.directory, filePath = arg.filePath, data = arg.data;
        return new Promise(function(resolve, reject) {
          return mkdirp(directory, function(mkdirErr) {
            if (mkdirErr != null) {
              return reject(mkdirErr);
            }
            return fs2.writeFile(filePath, data, function(writeErr) {
              if (writeErr != null) {
                return reject(writeErr);
              }
              return resolve();
            });
          });
        });
      },
      isEnabled: function(filePath) {
        return new Promise(/* @__PURE__ */ (function(_this) {
          return function(resolve, reject) {
            return fs2.stat(filePath, function(err, stat) {
              if (err != null) {
                return resolve(false);
              }
              return resolve(stat != null);
            });
          };
        })(this));
      },
      removeFile: function(filePath) {
        return new Promise(/* @__PURE__ */ (function(_this) {
          return function(resolve, reject) {
            return fs2.stat(filePath, function(statErr) {
              if (statErr != null) {
                return resolve();
              }
              return fs2.unlink(filePath, function(unlinkErr) {
                if (unlinkErr != null) {
                  return reject(unlinkErr);
                }
                return resolve();
              });
            });
          };
        })(this));
      }
    };
  }
});

// ../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/AutoLaunchMac.js
var require_AutoLaunchMac = __commonJS({
  "../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/AutoLaunchMac.js"(exports2, module2) {
    var applescript;
    var fileBasedUtilities;
    var untildify;
    var indexOf = [].indexOf || function(item) {
      for (var i = 0, l = this.length; i < l; i++) {
        if (i in this && this[i] === item) return i;
      }
      return -1;
    };
    applescript = require_applescript();
    untildify = require_untildify();
    fileBasedUtilities = require_fileBasedUtilities();
    module2.exports = {
      /* Public */
      enable: function(arg) {
        var appName, appPath, data, isHiddenOnLaunch, isHiddenValue, mac, programArguments, programArgumentsSection, properties;
        appName = arg.appName, appPath = arg.appPath, isHiddenOnLaunch = arg.isHiddenOnLaunch, mac = arg.mac;
        if (mac.useLaunchAgent) {
          programArguments = [appPath];
          if (isHiddenOnLaunch) {
            programArguments.push("--hidden");
          }
          programArgumentsSection = programArguments.map(function(argument) {
            return "    <string>" + argument + "</string>";
          }).join("\n");
          data = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n  <key>Label</key>\n  <string>' + appName + "</string>\n  <key>ProgramArguments</key>\n  <array>\n  " + programArgumentsSection + "\n  </array>\n  <key>RunAtLoad</key>\n  <true/>\n</dict>\n</plist>";
          return fileBasedUtilities.createFile({
            data,
            directory: this.getDirectory(),
            filePath: this.getFilePath(appName)
          });
        }
        isHiddenValue = isHiddenOnLaunch ? "true" : "false";
        properties = '{path:"' + appPath + '", hidden:' + isHiddenValue + ', name:"' + appName + '"}';
        return this.execApplescriptCommand("make login item at end with properties " + properties);
      },
      disable: function(appName, mac) {
        if (mac.useLaunchAgent) {
          return fileBasedUtilities.removeFile(this.getFilePath(appName));
        }
        return this.execApplescriptCommand('delete login item "' + appName + '"');
      },
      isEnabled: function(appName, mac) {
        if (mac.useLaunchAgent) {
          return fileBasedUtilities.isEnabled(this.getFilePath(appName));
        }
        return this.execApplescriptCommand("get the name of every login item").then(function(loginItems) {
          return loginItems != null && indexOf.call(loginItems, appName) >= 0;
        });
      },
      /* Private */
      execApplescriptCommand: function(commandSuffix) {
        return new Promise(function(resolve, reject) {
          return applescript.execString('tell application "System Events" to ' + commandSuffix, function(err, result) {
            if (err != null) {
              return reject(err);
            }
            return resolve(result);
          });
        });
      },
      getDirectory: function() {
        return untildify("~/Library/LaunchAgents/");
      },
      getFilePath: function(appName) {
        return "" + this.getDirectory() + appName + ".plist";
      }
    };
  }
});

// ../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/AutoLaunchLinux.js
var require_AutoLaunchLinux = __commonJS({
  "../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/AutoLaunchLinux.js"(exports2, module2) {
    var fileBasedUtilities;
    var untildify;
    untildify = require_untildify();
    fileBasedUtilities = require_fileBasedUtilities();
    module2.exports = {
      /* Public */
      enable: function(arg) {
        var appName, appPath, data, hiddenArg, isHiddenOnLaunch;
        appName = arg.appName, appPath = arg.appPath, isHiddenOnLaunch = arg.isHiddenOnLaunch;
        hiddenArg = isHiddenOnLaunch ? " --hidden" : "";
        data = "[Desktop Entry]\nType=Application\nVersion=1.0\nName=" + appName + "\nComment=" + appName + "startup script\nExec=" + appPath + hiddenArg + "\nStartupNotify=false\nTerminal=false";
        return fileBasedUtilities.createFile({
          data,
          directory: this.getDirectory(),
          filePath: this.getFilePath(appName)
        });
      },
      disable: function(appName) {
        return fileBasedUtilities.removeFile(this.getFilePath(appName));
      },
      isEnabled: function(appName) {
        return fileBasedUtilities.isEnabled(this.getFilePath(appName));
      },
      /* Private */
      getDirectory: function() {
        return untildify("~/.config/autostart/");
      },
      getFilePath: function(appName) {
        return "" + this.getDirectory() + appName + ".desktop";
      }
    };
  }
});

// ../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/index.js
var require_dist = __commonJS({
  "../../node_modules/.pnpm/auto-launch@5.0.6/node_modules/auto-launch/dist/index.js"(exports2, module2) {
    var AutoLaunch2;
    var isPathAbsolute;
    var bind = function(fn, me) {
      return function() {
        return fn.apply(me, arguments);
      };
    };
    isPathAbsolute = require_path_is_absolute();
    module2.exports = AutoLaunch2 = (function() {
      function AutoLaunch3(arg) {
        var isHidden, mac, name, path2, versions;
        name = arg.name, isHidden = arg.isHidden, mac = arg.mac, path2 = arg.path;
        this.fixOpts = bind(this.fixOpts, this);
        this.isEnabled = bind(this.isEnabled, this);
        this.disable = bind(this.disable, this);
        this.enable = bind(this.enable, this);
        if (name == null) {
          throw new Error("You must specify a name");
        }
        this.opts = {
          appName: name,
          isHiddenOnLaunch: isHidden != null ? isHidden : false,
          mac: mac != null ? mac : {}
        };
        versions = typeof process !== "undefined" && process !== null ? process.versions : void 0;
        if (path2 != null) {
          if (!isPathAbsolute(path2)) {
            throw new Error("path must be absolute");
          }
          this.opts.appPath = path2;
        } else if (versions != null && (versions.nw != null || versions["node-webkit"] != null || versions.electron != null)) {
          this.opts.appPath = process.execPath;
        } else {
          throw new Error("You must give a path (this is only auto-detected for NW.js and Electron apps)");
        }
        this.fixOpts();
        this.api = null;
        if (/^win/.test(process.platform)) {
          this.api = require_AutoLaunchWindows();
        } else if (/darwin/.test(process.platform)) {
          this.api = require_AutoLaunchMac();
        } else if (/linux/.test(process.platform) || /freebsd/.test(process.platform)) {
          this.api = require_AutoLaunchLinux();
        } else {
          throw new Error("Unsupported platform");
        }
      }
      AutoLaunch3.prototype.enable = function() {
        return this.api.enable(this.opts);
      };
      AutoLaunch3.prototype.disable = function() {
        return this.api.disable(this.opts.appName, this.opts.mac);
      };
      AutoLaunch3.prototype.isEnabled = function() {
        return this.api.isEnabled(this.opts.appName, this.opts.mac);
      };
      AutoLaunch3.prototype.fixMacExecPath = function(path2, macOptions) {
        path2 = path2.replace(/(^.+?[^\/]+?\.app)\/Contents\/(Frameworks\/((\1|[^\/]+?) Helper)\.app\/Contents\/MacOS\/\3|MacOS\/Electron)/, "$1");
        if (!macOptions.useLaunchAgent) {
          path2 = path2.replace(/\.app\/Contents\/MacOS\/[^\/]*$/, ".app");
        }
        return path2;
      };
      AutoLaunch3.prototype.fixOpts = function() {
        var tempPath;
        this.opts.appPath = this.opts.appPath.replace(/\/$/, "");
        if (/darwin/.test(process.platform)) {
          this.opts.appPath = this.fixMacExecPath(this.opts.appPath, this.opts.mac);
        }
        if (this.opts.appPath.indexOf("/") !== -1) {
          tempPath = this.opts.appPath.split("/");
          this.opts.appName = tempPath[tempPath.length - 1];
        } else if (this.opts.appPath.indexOf("\\") !== -1) {
          tempPath = this.opts.appPath.split("\\");
          this.opts.appName = tempPath[tempPath.length - 1];
          this.opts.appName = this.opts.appName.substr(0, this.opts.appName.length - ".exe".length);
        }
        if (/darwin/.test(process.platform)) {
          if (this.opts.appName.indexOf(".app", this.opts.appName.length - ".app".length) !== -1) {
            return this.opts.appName = this.opts.appName.substr(0, this.opts.appName.length - ".app".length);
          }
        }
      };
      return AutoLaunch3;
    })();
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/electron-log-preload.js
var require_electron_log_preload = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/electron-log-preload.js"(exports2, module2) {
    "use strict";
    var electron = {};
    try {
      electron = require("electron");
    } catch (e) {
    }
    if (electron.ipcRenderer) {
      initialize(electron);
    }
    if (typeof module2 === "object") {
      module2.exports = initialize;
    }
    function initialize({ contextBridge, ipcRenderer }) {
      if (!ipcRenderer) {
        return;
      }
      ipcRenderer.on("__ELECTRON_LOG_IPC__", (_, message) => {
        window.postMessage({ cmd: "message", ...message });
      });
      ipcRenderer.invoke("__ELECTRON_LOG__", { cmd: "getOptions" }).catch((e) => console.error(new Error(
        `electron-log isn't initialized in the main process. Please call log.initialize() before. ${e.message}`
      )));
      const electronLog = {
        sendToMain(message) {
          try {
            ipcRenderer.send("__ELECTRON_LOG__", message);
          } catch (e) {
            console.error("electronLog.sendToMain ", e, "data:", message);
            ipcRenderer.send("__ELECTRON_LOG__", {
              cmd: "errorHandler",
              error: { message: e?.message, stack: e?.stack },
              errorName: "sendToMain"
            });
          }
        },
        log(...data) {
          electronLog.sendToMain({ data, level: "info" });
        }
      };
      for (const level of ["error", "warn", "info", "verbose", "debug", "silly"]) {
        electronLog[level] = (...data) => electronLog.sendToMain({
          data,
          level
        });
      }
      if (contextBridge && process.contextIsolated) {
        try {
          contextBridge.exposeInMainWorld("__electronLog", electronLog);
        } catch {
        }
      }
      if (typeof window === "object") {
        window.__electronLog = electronLog;
      } else {
        __electronLog = electronLog;
      }
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/scope.js
var require_scope = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/scope.js"(exports2, module2) {
    "use strict";
    module2.exports = scopeFactory;
    function scopeFactory(logger) {
      return Object.defineProperties(scope, {
        defaultLabel: { value: "", writable: true },
        labelPadding: { value: true, writable: true },
        maxLabelLength: { value: 0, writable: true },
        labelLength: {
          get() {
            switch (typeof scope.labelPadding) {
              case "boolean":
                return scope.labelPadding ? scope.maxLabelLength : 0;
              case "number":
                return scope.labelPadding;
              default:
                return 0;
            }
          }
        }
      });
      function scope(label) {
        scope.maxLabelLength = Math.max(scope.maxLabelLength, label.length);
        const newScope = {};
        for (const level of logger.levels) {
          newScope[level] = (...d) => logger.logData(d, { level, scope: label });
        }
        newScope.log = newScope.info;
        return newScope;
      }
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/Buffering.js
var require_Buffering = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/Buffering.js"(exports2, module2) {
    "use strict";
    var Buffering = class {
      constructor({ processMessage }) {
        this.processMessage = processMessage;
        this.buffer = [];
        this.enabled = false;
        this.begin = this.begin.bind(this);
        this.commit = this.commit.bind(this);
        this.reject = this.reject.bind(this);
      }
      addMessage(message) {
        this.buffer.push(message);
      }
      begin() {
        this.enabled = [];
      }
      commit() {
        this.enabled = false;
        this.buffer.forEach((item) => this.processMessage(item));
        this.buffer = [];
      }
      reject() {
        this.enabled = false;
        this.buffer = [];
      }
    };
    module2.exports = Buffering;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/Logger.js
var require_Logger = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/Logger.js"(exports2, module2) {
    "use strict";
    var scopeFactory = require_scope();
    var Buffering = require_Buffering();
    var Logger = class _Logger {
      static instances = {};
      dependencies = {};
      errorHandler = null;
      eventLogger = null;
      functions = {};
      hooks = [];
      isDev = false;
      levels = null;
      logId = null;
      scope = null;
      transports = {};
      variables = {};
      constructor({
        allowUnknownLevel = false,
        dependencies = {},
        errorHandler,
        eventLogger,
        initializeFn,
        isDev: isDev2 = false,
        levels = ["error", "warn", "info", "verbose", "debug", "silly"],
        logId,
        transportFactories = {},
        variables
      } = {}) {
        this.addLevel = this.addLevel.bind(this);
        this.create = this.create.bind(this);
        this.initialize = this.initialize.bind(this);
        this.logData = this.logData.bind(this);
        this.processMessage = this.processMessage.bind(this);
        this.allowUnknownLevel = allowUnknownLevel;
        this.buffering = new Buffering(this);
        this.dependencies = dependencies;
        this.initializeFn = initializeFn;
        this.isDev = isDev2;
        this.levels = levels;
        this.logId = logId;
        this.scope = scopeFactory(this);
        this.transportFactories = transportFactories;
        this.variables = variables || {};
        for (const name of this.levels) {
          this.addLevel(name, false);
        }
        this.log = this.info;
        this.functions.log = this.log;
        this.errorHandler = errorHandler;
        errorHandler?.setOptions({ ...dependencies, logFn: this.error });
        this.eventLogger = eventLogger;
        eventLogger?.setOptions({ ...dependencies, logger: this });
        for (const [name, factory] of Object.entries(transportFactories)) {
          this.transports[name] = factory(this, dependencies);
        }
        _Logger.instances[logId] = this;
      }
      static getInstance({ logId }) {
        return this.instances[logId] || this.instances.default;
      }
      addLevel(level, index = this.levels.length) {
        if (index !== false) {
          this.levels.splice(index, 0, level);
        }
        this[level] = (...args) => this.logData(args, { level });
        this.functions[level] = this[level];
      }
      catchErrors(options) {
        this.processMessage(
          {
            data: ["log.catchErrors is deprecated. Use log.errorHandler instead"],
            level: "warn"
          },
          { transports: ["console"] }
        );
        return this.errorHandler.startCatching(options);
      }
      create(options) {
        if (typeof options === "string") {
          options = { logId: options };
        }
        return new _Logger({
          dependencies: this.dependencies,
          errorHandler: this.errorHandler,
          initializeFn: this.initializeFn,
          isDev: this.isDev,
          transportFactories: this.transportFactories,
          variables: { ...this.variables },
          ...options
        });
      }
      compareLevels(passLevel, checkLevel, levels = this.levels) {
        const pass = levels.indexOf(passLevel);
        const check = levels.indexOf(checkLevel);
        if (check === -1 || pass === -1) {
          return true;
        }
        return check <= pass;
      }
      initialize(options = {}) {
        this.initializeFn({ logger: this, ...this.dependencies, ...options });
      }
      logData(data, options = {}) {
        if (this.buffering.enabled) {
          this.buffering.addMessage({ data, date: /* @__PURE__ */ new Date(), ...options });
        } else {
          this.processMessage({ data, ...options });
        }
      }
      processMessage(message, { transports = this.transports } = {}) {
        if (message.cmd === "errorHandler") {
          this.errorHandler.handle(message.error, {
            errorName: message.errorName,
            processType: "renderer",
            showDialog: Boolean(message.showDialog)
          });
          return;
        }
        let level = message.level;
        if (!this.allowUnknownLevel) {
          level = this.levels.includes(message.level) ? message.level : "info";
        }
        const normalizedMessage = {
          date: /* @__PURE__ */ new Date(),
          logId: this.logId,
          ...message,
          level,
          variables: {
            ...this.variables,
            ...message.variables
          }
        };
        for (const [transName, transFn] of this.transportEntries(transports)) {
          if (typeof transFn !== "function" || transFn.level === false) {
            continue;
          }
          if (!this.compareLevels(transFn.level, message.level)) {
            continue;
          }
          try {
            const transformedMsg = this.hooks.reduce((msg, hook) => {
              return msg ? hook(msg, transFn, transName) : msg;
            }, normalizedMessage);
            if (transformedMsg) {
              transFn({ ...transformedMsg, data: [...transformedMsg.data] });
            }
          } catch (e) {
            this.processInternalErrorFn(e);
          }
        }
      }
      processInternalErrorFn(_e) {
      }
      transportEntries(transports = this.transports) {
        const transportArray = Array.isArray(transports) ? transports : Object.entries(transports);
        return transportArray.map((item) => {
          switch (typeof item) {
            case "string":
              return this.transports[item] ? [item, this.transports[item]] : null;
            case "function":
              return [item.name, item];
            default:
              return Array.isArray(item) ? item : null;
          }
        }).filter(Boolean);
      }
    };
    module2.exports = Logger;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/lib/RendererErrorHandler.js
var require_RendererErrorHandler = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/lib/RendererErrorHandler.js"(exports2, module2) {
    "use strict";
    var consoleError = console.error;
    var RendererErrorHandler = class {
      logFn = null;
      onError = null;
      showDialog = false;
      preventDefault = true;
      constructor({ logFn = null } = {}) {
        this.handleError = this.handleError.bind(this);
        this.handleRejection = this.handleRejection.bind(this);
        this.startCatching = this.startCatching.bind(this);
        this.logFn = logFn;
      }
      handle(error, {
        logFn = this.logFn,
        errorName = "",
        onError = this.onError,
        showDialog = this.showDialog
      } = {}) {
        try {
          if (onError?.({ error, errorName, processType: "renderer" }) !== false) {
            logFn({ error, errorName, showDialog });
          }
        } catch {
          consoleError(error);
        }
      }
      setOptions({ logFn, onError, preventDefault, showDialog }) {
        if (typeof logFn === "function") {
          this.logFn = logFn;
        }
        if (typeof onError === "function") {
          this.onError = onError;
        }
        if (typeof preventDefault === "boolean") {
          this.preventDefault = preventDefault;
        }
        if (typeof showDialog === "boolean") {
          this.showDialog = showDialog;
        }
      }
      startCatching({ onError, showDialog } = {}) {
        if (this.isActive) {
          return;
        }
        this.isActive = true;
        this.setOptions({ onError, showDialog });
        window.addEventListener("error", (event) => {
          this.preventDefault && event.preventDefault?.();
          this.handleError(event.error || event);
        });
        window.addEventListener("unhandledrejection", (event) => {
          this.preventDefault && event.preventDefault?.();
          this.handleRejection(event.reason || event);
        });
      }
      handleError(error) {
        this.handle(error, { errorName: "Unhandled" });
      }
      handleRejection(reason) {
        const error = reason instanceof Error ? reason : new Error(JSON.stringify(reason));
        this.handle(error, { errorName: "Unhandled rejection" });
      }
    };
    module2.exports = RendererErrorHandler;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/transforms/transform.js
var require_transform = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/transforms/transform.js"(exports2, module2) {
    "use strict";
    module2.exports = { transform };
    function transform({
      logger,
      message,
      transport,
      initialData = message?.data || [],
      transforms = transport?.transforms
    }) {
      return transforms.reduce((data, trans) => {
        if (typeof trans === "function") {
          return trans({ data, logger, message, transport });
        }
        return data;
      }, initialData);
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/lib/transports/console.js
var require_console = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/lib/transports/console.js"(exports2, module2) {
    "use strict";
    var { transform } = require_transform();
    module2.exports = consoleTransportRendererFactory;
    var consoleMethods = {
      error: console.error,
      warn: console.warn,
      info: console.info,
      verbose: console.info,
      debug: console.debug,
      silly: console.debug,
      log: console.log
    };
    function consoleTransportRendererFactory(logger) {
      return Object.assign(transport, {
        format: "{h}:{i}:{s}.{ms}{scope} \u203A {text}",
        transforms: [formatDataFn],
        writeFn({ message: { level, data } }) {
          const consoleLogFn = consoleMethods[level] || consoleMethods.info;
          setTimeout(() => consoleLogFn(...data));
        }
      });
      function transport(message) {
        transport.writeFn({
          message: { ...message, data: transform({ logger, message, transport }) }
        });
      }
    }
    function formatDataFn({
      data = [],
      logger = {},
      message = {},
      transport = {}
    }) {
      if (typeof transport.format === "function") {
        return transport.format({
          data,
          level: message?.level || "info",
          logger,
          message,
          transport
        });
      }
      if (typeof transport.format !== "string") {
        return data;
      }
      data.unshift(transport.format);
      if (typeof data[1] === "string" && data[1].match(/%[1cdfiOos]/)) {
        data = [`${data[0]}${data[1]}`, ...data.slice(2)];
      }
      const date = message.date || /* @__PURE__ */ new Date();
      data[0] = data[0].replace(/\{(\w+)}/g, (substring, name) => {
        switch (name) {
          case "level":
            return message.level;
          case "logId":
            return message.logId;
          case "scope": {
            const scope = message.scope || logger.scope?.defaultLabel;
            return scope ? ` (${scope})` : "";
          }
          case "text":
            return "";
          case "y":
            return date.getFullYear().toString(10);
          case "m":
            return (date.getMonth() + 1).toString(10).padStart(2, "0");
          case "d":
            return date.getDate().toString(10).padStart(2, "0");
          case "h":
            return date.getHours().toString(10).padStart(2, "0");
          case "i":
            return date.getMinutes().toString(10).padStart(2, "0");
          case "s":
            return date.getSeconds().toString(10).padStart(2, "0");
          case "ms":
            return date.getMilliseconds().toString(10).padStart(3, "0");
          case "iso":
            return date.toISOString();
          default:
            return message.variables?.[name] || substring;
        }
      }).trim();
      return data;
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/lib/transports/ipc.js
var require_ipc = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/lib/transports/ipc.js"(exports2, module2) {
    "use strict";
    var { transform } = require_transform();
    module2.exports = ipcTransportRendererFactory;
    var RESTRICTED_TYPES = /* @__PURE__ */ new Set([Promise, WeakMap, WeakSet]);
    function ipcTransportRendererFactory(logger) {
      return Object.assign(transport, {
        depth: 5,
        transforms: [serializeFn]
      });
      function transport(message) {
        if (!window.__electronLog) {
          logger.processMessage(
            {
              data: ["electron-log: logger isn't initialized in the main process"],
              level: "error"
            },
            { transports: ["console"] }
          );
          return;
        }
        try {
          const serialized = transform({
            initialData: message,
            logger,
            message,
            transport
          });
          __electronLog.sendToMain(serialized);
        } catch (e) {
          logger.transports.console({
            data: ["electronLog.transports.ipc", e, "data:", message.data],
            level: "error"
          });
        }
      }
    }
    function isPrimitive(value) {
      return Object(value) !== value;
    }
    function serializeFn({
      data,
      depth,
      seen = /* @__PURE__ */ new WeakSet(),
      transport = {}
    } = {}) {
      const actualDepth = depth || transport.depth || 5;
      if (seen.has(data)) {
        return "[Circular]";
      }
      if (actualDepth < 1) {
        if (isPrimitive(data)) {
          return data;
        }
        if (Array.isArray(data)) {
          return "[Array]";
        }
        return `[${typeof data}]`;
      }
      if (["function", "symbol"].includes(typeof data)) {
        return data.toString();
      }
      if (isPrimitive(data)) {
        return data;
      }
      if (RESTRICTED_TYPES.has(data.constructor)) {
        return `[${data.constructor.name}]`;
      }
      if (Array.isArray(data)) {
        return data.map((item) => serializeFn({
          data: item,
          depth: actualDepth - 1,
          seen
        }));
      }
      if (data instanceof Date) {
        return data.toISOString();
      }
      if (data instanceof Error) {
        return data.stack;
      }
      if (data instanceof Map) {
        return new Map(
          Array.from(data).map(([key, value]) => [
            serializeFn({ data: key, depth: actualDepth - 1, seen }),
            serializeFn({ data: value, depth: actualDepth - 1, seen })
          ])
        );
      }
      if (data instanceof Set) {
        return new Set(
          Array.from(data).map(
            (val) => serializeFn({ data: val, depth: actualDepth - 1, seen })
          )
        );
      }
      seen.add(data);
      return Object.fromEntries(
        Object.entries(data).map(
          ([key, value]) => [
            key,
            serializeFn({ data: value, depth: actualDepth - 1, seen })
          ]
        )
      );
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/index.js
var require_renderer = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/renderer/index.js"(exports2, module2) {
    "use strict";
    var Logger = require_Logger();
    var RendererErrorHandler = require_RendererErrorHandler();
    var transportConsole = require_console();
    var transportIpc = require_ipc();
    if (typeof process === "object" && process.type === "browser") {
      console.warn(
        "electron-log/renderer is loaded in the main process. It could cause unexpected behaviour."
      );
    }
    module2.exports = createLogger();
    module2.exports.Logger = Logger;
    module2.exports.default = module2.exports;
    function createLogger() {
      const logger = new Logger({
        allowUnknownLevel: true,
        errorHandler: new RendererErrorHandler(),
        initializeFn: () => {
        },
        logId: "default",
        transportFactories: {
          console: transportConsole,
          ipc: transportIpc
        },
        variables: {
          processType: "renderer"
        }
      });
      logger.errorHandler.setOptions({
        logFn({ error, errorName, showDialog }) {
          logger.transports.console({
            data: [errorName, error].filter(Boolean),
            level: "error"
          });
          logger.transports.ipc({
            cmd: "errorHandler",
            error: {
              cause: error?.cause,
              code: error?.code,
              name: error?.name,
              message: error?.message,
              stack: error?.stack
            },
            errorName,
            logId: logger.logId,
            showDialog
          });
        }
      });
      if (typeof window === "object") {
        window.addEventListener("message", (event) => {
          const { cmd, logId, ...message } = event.data || {};
          const instance = Logger.getInstance({ logId });
          if (cmd === "message") {
            instance.processMessage(message, { transports: ["console"] });
          }
        });
      }
      return new Proxy(logger, {
        get(target, prop) {
          if (typeof target[prop] !== "undefined") {
            return target[prop];
          }
          return (...data) => logger.logData(data, { level: prop });
        }
      });
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/packageJson.js
var require_packageJson = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/packageJson.js"(exports2, module2) {
    "use strict";
    var fs2 = require("fs");
    var path2 = require("path");
    module2.exports = {
      findAndReadPackageJson,
      tryReadJsonAt
    };
    function findAndReadPackageJson() {
      return tryReadJsonAt(getMainModulePath()) || tryReadJsonAt(extractPathFromArgs()) || tryReadJsonAt(process.resourcesPath, "app.asar") || tryReadJsonAt(process.resourcesPath, "app") || tryReadJsonAt(process.cwd()) || { name: void 0, version: void 0 };
    }
    function tryReadJsonAt(...searchPaths) {
      if (!searchPaths[0]) {
        return void 0;
      }
      try {
        const searchPath = path2.join(...searchPaths);
        const fileName = findUp("package.json", searchPath);
        if (!fileName) {
          return void 0;
        }
        const json = JSON.parse(fs2.readFileSync(fileName, "utf8"));
        const name = json?.productName || json?.name;
        if (!name || name.toLowerCase() === "electron") {
          return void 0;
        }
        if (name) {
          return { name, version: json?.version };
        }
        return void 0;
      } catch (e) {
        return void 0;
      }
    }
    function findUp(fileName, cwd) {
      let currentPath = cwd;
      while (true) {
        const parsedPath = path2.parse(currentPath);
        const root = parsedPath.root;
        const dir = parsedPath.dir;
        if (fs2.existsSync(path2.join(currentPath, fileName))) {
          return path2.resolve(path2.join(currentPath, fileName));
        }
        if (currentPath === root) {
          return null;
        }
        currentPath = dir;
      }
    }
    function extractPathFromArgs() {
      const matchedArgs = process.argv.filter((arg) => {
        return arg.indexOf("--user-data-dir=") === 0;
      });
      if (matchedArgs.length === 0 || typeof matchedArgs[0] !== "string") {
        return null;
      }
      const userDataDir = matchedArgs[0];
      return userDataDir.replace("--user-data-dir=", "");
    }
    function getMainModulePath() {
      try {
        return require.main?.filename;
      } catch {
        return void 0;
      }
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/NodeExternalApi.js
var require_NodeExternalApi = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/NodeExternalApi.js"(exports2, module2) {
    "use strict";
    var childProcess = require("child_process");
    var os = require("os");
    var path2 = require("path");
    var packageJson = require_packageJson();
    var NodeExternalApi = class {
      appName = void 0;
      appPackageJson = void 0;
      platform = process.platform;
      getAppLogPath(appName = this.getAppName()) {
        if (this.platform === "darwin") {
          return path2.join(this.getSystemPathHome(), "Library/Logs", appName);
        }
        return path2.join(this.getAppUserDataPath(appName), "logs");
      }
      getAppName() {
        const appName = this.appName || this.getAppPackageJson()?.name;
        if (!appName) {
          throw new Error(
            "electron-log can't determine the app name. It tried these methods:\n1. Use `electron.app.name`\n2. Use productName or name from the nearest package.json`\nYou can also set it through log.transports.file.setAppName()"
          );
        }
        return appName;
      }
      /**
       * @private
       * @returns {undefined}
       */
      getAppPackageJson() {
        if (typeof this.appPackageJson !== "object") {
          this.appPackageJson = packageJson.findAndReadPackageJson();
        }
        return this.appPackageJson;
      }
      getAppUserDataPath(appName = this.getAppName()) {
        return appName ? path2.join(this.getSystemPathAppData(), appName) : void 0;
      }
      getAppVersion() {
        return this.getAppPackageJson()?.version;
      }
      getElectronLogPath() {
        return this.getAppLogPath();
      }
      getMacOsVersion() {
        const release = Number(os.release().split(".")[0]);
        if (release <= 19) {
          return `10.${release - 4}`;
        }
        return release - 9;
      }
      /**
       * @protected
       * @returns {string}
       */
      getOsVersion() {
        let osName = os.type().replace("_", " ");
        let osVersion = os.release();
        if (osName === "Darwin") {
          osName = "macOS";
          osVersion = this.getMacOsVersion();
        }
        return `${osName} ${osVersion}`;
      }
      /**
       * @return {PathVariables}
       */
      getPathVariables() {
        const appName = this.getAppName();
        const appVersion = this.getAppVersion();
        const self = this;
        return {
          appData: this.getSystemPathAppData(),
          appName,
          appVersion,
          get electronDefaultDir() {
            return self.getElectronLogPath();
          },
          home: this.getSystemPathHome(),
          libraryDefaultDir: this.getAppLogPath(appName),
          libraryTemplate: this.getAppLogPath("{appName}"),
          temp: this.getSystemPathTemp(),
          userData: this.getAppUserDataPath(appName)
        };
      }
      getSystemPathAppData() {
        const home = this.getSystemPathHome();
        switch (this.platform) {
          case "darwin": {
            return path2.join(home, "Library/Application Support");
          }
          case "win32": {
            return process.env.APPDATA || path2.join(home, "AppData/Roaming");
          }
          default: {
            return process.env.XDG_CONFIG_HOME || path2.join(home, ".config");
          }
        }
      }
      getSystemPathHome() {
        return os.homedir?.() || process.env.HOME;
      }
      getSystemPathTemp() {
        return os.tmpdir();
      }
      getVersions() {
        return {
          app: `${this.getAppName()} ${this.getAppVersion()}`,
          electron: void 0,
          os: this.getOsVersion()
        };
      }
      isDev() {
        return process.env.NODE_ENV === "development" || process.env.ELECTRON_IS_DEV === "1";
      }
      isElectron() {
        return Boolean(process.versions.electron);
      }
      onAppEvent(_eventName, _handler) {
      }
      onAppReady(handler) {
        handler();
      }
      onEveryWebContentsEvent(eventName, handler) {
      }
      /**
       * Listen to async messages sent from opposite process
       * @param {string} channel
       * @param {function} listener
       */
      onIpc(channel, listener) {
      }
      onIpcInvoke(channel, listener) {
      }
      /**
       * @param {string} url
       * @param {Function} [logFunction]
       */
      openUrl(url, logFunction = console.error) {
        const startMap = { darwin: "open", win32: "start", linux: "xdg-open" };
        const start = startMap[process.platform] || "xdg-open";
        childProcess.exec(`${start} ${url}`, {}, (err) => {
          if (err) {
            logFunction(err);
          }
        });
      }
      setAppName(appName) {
        this.appName = appName;
      }
      setPlatform(platform) {
        this.platform = platform;
      }
      setPreloadFileForSessions({
        filePath,
        // eslint-disable-line no-unused-vars
        includeFutureSession = true,
        // eslint-disable-line no-unused-vars
        getSessions = () => []
        // eslint-disable-line no-unused-vars
      }) {
      }
      /**
       * Sent a message to opposite process
       * @param {string} channel
       * @param {any} message
       */
      sendIpc(channel, message) {
      }
      showErrorBox(title, message) {
      }
    };
    module2.exports = NodeExternalApi;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/main/ElectronExternalApi.js
var require_ElectronExternalApi = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/main/ElectronExternalApi.js"(exports2, module2) {
    "use strict";
    var path2 = require("path");
    var NodeExternalApi = require_NodeExternalApi();
    var ElectronExternalApi = class extends NodeExternalApi {
      /**
       * @type {typeof Electron}
       */
      electron = void 0;
      /**
       * @param {object} options
       * @param {typeof Electron} [options.electron]
       */
      constructor({ electron } = {}) {
        super();
        this.electron = electron;
      }
      getAppName() {
        let appName;
        try {
          appName = this.appName || this.electron.app?.name || this.electron.app?.getName();
        } catch {
        }
        return appName || super.getAppName();
      }
      getAppUserDataPath(appName) {
        return this.getPath("userData") || super.getAppUserDataPath(appName);
      }
      getAppVersion() {
        let appVersion;
        try {
          appVersion = this.electron.app?.getVersion();
        } catch {
        }
        return appVersion || super.getAppVersion();
      }
      getElectronLogPath() {
        return this.getPath("logs") || super.getElectronLogPath();
      }
      /**
       * @private
       * @param {any} name
       * @returns {string|undefined}
       */
      getPath(name) {
        try {
          return this.electron.app?.getPath(name);
        } catch {
          return void 0;
        }
      }
      getVersions() {
        return {
          app: `${this.getAppName()} ${this.getAppVersion()}`,
          electron: `Electron ${process.versions.electron}`,
          os: this.getOsVersion()
        };
      }
      getSystemPathAppData() {
        return this.getPath("appData") || super.getSystemPathAppData();
      }
      isDev() {
        if (this.electron.app?.isPackaged !== void 0) {
          return !this.electron.app.isPackaged;
        }
        if (typeof process.execPath === "string") {
          const execFileName = path2.basename(process.execPath).toLowerCase();
          return execFileName.startsWith("electron");
        }
        return super.isDev();
      }
      onAppEvent(eventName, handler) {
        this.electron.app?.on(eventName, handler);
        return () => {
          this.electron.app?.off(eventName, handler);
        };
      }
      onAppReady(handler) {
        if (this.electron.app?.isReady()) {
          handler();
        } else if (this.electron.app?.once) {
          this.electron.app?.once("ready", handler);
        } else {
          handler();
        }
      }
      onEveryWebContentsEvent(eventName, handler) {
        this.electron.webContents?.getAllWebContents()?.forEach((webContents) => {
          webContents.on(eventName, handler);
        });
        this.electron.app?.on("web-contents-created", onWebContentsCreated);
        return () => {
          this.electron.webContents?.getAllWebContents().forEach((webContents) => {
            webContents.off(eventName, handler);
          });
          this.electron.app?.off("web-contents-created", onWebContentsCreated);
        };
        function onWebContentsCreated(_, webContents) {
          webContents.on(eventName, handler);
        }
      }
      /**
       * Listen to async messages sent from opposite process
       * @param {string} channel
       * @param {function} listener
       */
      onIpc(channel, listener) {
        this.electron.ipcMain?.on(channel, listener);
      }
      onIpcInvoke(channel, listener) {
        this.electron.ipcMain?.handle?.(channel, listener);
      }
      /**
       * @param {string} url
       * @param {Function} [logFunction]
       */
      openUrl(url, logFunction = console.error) {
        this.electron.shell?.openExternal(url).catch(logFunction);
      }
      setPreloadFileForSessions({
        filePath,
        includeFutureSession = true,
        getSessions = () => [this.electron.session?.defaultSession]
      }) {
        for (const session of getSessions().filter(Boolean)) {
          setPreload(session);
        }
        if (includeFutureSession) {
          this.onAppEvent("session-created", (session) => {
            setPreload(session);
          });
        }
        function setPreload(session) {
          if (typeof session.registerPreloadScript === "function") {
            session.registerPreloadScript({
              filePath,
              id: "electron-log-preload",
              type: "frame"
            });
          } else {
            session.setPreloads([...session.getPreloads(), filePath]);
          }
        }
      }
      /**
       * Sent a message to opposite process
       * @param {string} channel
       * @param {any} message
       */
      sendIpc(channel, message) {
        this.electron.BrowserWindow?.getAllWindows()?.forEach((wnd) => {
          if (wnd.webContents?.isDestroyed() === false && wnd.webContents?.isCrashed() === false) {
            wnd.webContents.send(channel, message);
          }
        });
      }
      showErrorBox(title, message) {
        this.electron.dialog?.showErrorBox(title, message);
      }
    };
    module2.exports = ElectronExternalApi;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/main/initialize.js
var require_initialize = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/main/initialize.js"(exports2, module2) {
    "use strict";
    var fs2 = require("fs");
    var os = require("os");
    var path2 = require("path");
    var preloadInitializeFn = require_electron_log_preload();
    var preloadInitialized = false;
    var spyConsoleInitialized = false;
    module2.exports = {
      initialize({
        externalApi,
        getSessions,
        includeFutureSession,
        logger,
        preload = true,
        spyRendererConsole = false
      }) {
        externalApi.onAppReady(() => {
          try {
            if (preload) {
              initializePreload({
                externalApi,
                getSessions,
                includeFutureSession,
                logger,
                preloadOption: preload
              });
            }
            if (spyRendererConsole) {
              initializeSpyRendererConsole({ externalApi, logger });
            }
          } catch (err) {
            logger.warn(err);
          }
        });
      }
    };
    function initializePreload({
      externalApi,
      getSessions,
      includeFutureSession,
      logger,
      preloadOption
    }) {
      let preloadPath = typeof preloadOption === "string" ? preloadOption : void 0;
      if (preloadInitialized) {
        logger.warn(new Error("log.initialize({ preload }) already called").stack);
        return;
      }
      preloadInitialized = true;
      try {
        preloadPath = path2.resolve(
          __dirname,
          "../renderer/electron-log-preload.js"
        );
      } catch {
      }
      if (!preloadPath || !fs2.existsSync(preloadPath)) {
        preloadPath = path2.join(
          externalApi.getAppUserDataPath() || os.tmpdir(),
          "electron-log-preload.js"
        );
        const preloadCode = `
      try {
        (${preloadInitializeFn.toString()})(require('electron'));
      } catch(e) {
        console.error(e);
      }
    `;
        fs2.writeFileSync(preloadPath, preloadCode, "utf8");
      }
      externalApi.setPreloadFileForSessions({
        filePath: preloadPath,
        includeFutureSession,
        getSessions
      });
    }
    function initializeSpyRendererConsole({ externalApi, logger }) {
      if (spyConsoleInitialized) {
        logger.warn(
          new Error("log.initialize({ spyRendererConsole }) already called").stack
        );
        return;
      }
      spyConsoleInitialized = true;
      const levels = ["debug", "info", "warn", "error"];
      externalApi.onEveryWebContentsEvent(
        "console-message",
        (event, level, message) => {
          logger.processMessage({
            data: [message],
            level: levels[level],
            variables: { processType: "renderer" }
          });
        }
      );
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/ErrorHandler.js
var require_ErrorHandler = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/ErrorHandler.js"(exports2, module2) {
    "use strict";
    var ErrorHandler = class {
      externalApi = void 0;
      isActive = false;
      logFn = void 0;
      onError = void 0;
      showDialog = true;
      constructor({
        externalApi,
        logFn = void 0,
        onError = void 0,
        showDialog = void 0
      } = {}) {
        this.createIssue = this.createIssue.bind(this);
        this.handleError = this.handleError.bind(this);
        this.handleRejection = this.handleRejection.bind(this);
        this.setOptions({ externalApi, logFn, onError, showDialog });
        this.startCatching = this.startCatching.bind(this);
        this.stopCatching = this.stopCatching.bind(this);
      }
      handle(error, {
        logFn = this.logFn,
        onError = this.onError,
        processType = "browser",
        showDialog = this.showDialog,
        errorName = ""
      } = {}) {
        error = normalizeError(error);
        try {
          if (typeof onError === "function") {
            const versions = this.externalApi?.getVersions() || {};
            const createIssue = this.createIssue;
            const result = onError({
              createIssue,
              error,
              errorName,
              processType,
              versions
            });
            if (result === false) {
              return;
            }
          }
          errorName ? logFn(errorName, error) : logFn(error);
          if (showDialog && !errorName.includes("rejection") && this.externalApi) {
            this.externalApi.showErrorBox(
              `A JavaScript error occurred in the ${processType} process`,
              error.stack
            );
          }
        } catch {
          console.error(error);
        }
      }
      setOptions({ externalApi, logFn, onError, showDialog }) {
        if (typeof externalApi === "object") {
          this.externalApi = externalApi;
        }
        if (typeof logFn === "function") {
          this.logFn = logFn;
        }
        if (typeof onError === "function") {
          this.onError = onError;
        }
        if (typeof showDialog === "boolean") {
          this.showDialog = showDialog;
        }
      }
      startCatching({ onError, showDialog } = {}) {
        if (this.isActive) {
          return;
        }
        this.isActive = true;
        this.setOptions({ onError, showDialog });
        process.on("uncaughtException", this.handleError);
        process.on("unhandledRejection", this.handleRejection);
      }
      stopCatching() {
        this.isActive = false;
        process.removeListener("uncaughtException", this.handleError);
        process.removeListener("unhandledRejection", this.handleRejection);
      }
      createIssue(pageUrl, queryParams) {
        this.externalApi?.openUrl(
          `${pageUrl}?${new URLSearchParams(queryParams).toString()}`
        );
      }
      handleError(error) {
        this.handle(error, { errorName: "Unhandled" });
      }
      handleRejection(reason) {
        const error = reason instanceof Error ? reason : new Error(JSON.stringify(reason));
        this.handle(error, { errorName: "Unhandled rejection" });
      }
    };
    function normalizeError(e) {
      if (e instanceof Error) {
        return e;
      }
      if (e && typeof e === "object") {
        if (e.message) {
          return Object.assign(new Error(e.message), e);
        }
        try {
          return new Error(JSON.stringify(e));
        } catch (serErr) {
          return new Error(`Couldn't normalize error ${String(e)}: ${serErr}`);
        }
      }
      return new Error(`Can't normalize error ${String(e)}`);
    }
    module2.exports = ErrorHandler;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/EventLogger.js
var require_EventLogger = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/EventLogger.js"(exports2, module2) {
    "use strict";
    var EventLogger = class {
      disposers = [];
      format = "{eventSource}#{eventName}:";
      formatters = {
        app: {
          "certificate-error": ({ args }) => {
            return this.arrayToObject(args.slice(1, 4), [
              "url",
              "error",
              "certificate"
            ]);
          },
          "child-process-gone": ({ args }) => {
            return args.length === 1 ? args[0] : args;
          },
          "render-process-gone": ({ args: [webContents, details] }) => {
            return details && typeof details === "object" ? { ...details, ...this.getWebContentsDetails(webContents) } : [];
          }
        },
        webContents: {
          "console-message": ({ args: [level, message, line, sourceId] }) => {
            if (level < 3) {
              return void 0;
            }
            return { message, source: `${sourceId}:${line}` };
          },
          "did-fail-load": ({ args }) => {
            return this.arrayToObject(args, [
              "errorCode",
              "errorDescription",
              "validatedURL",
              "isMainFrame",
              "frameProcessId",
              "frameRoutingId"
            ]);
          },
          "did-fail-provisional-load": ({ args }) => {
            return this.arrayToObject(args, [
              "errorCode",
              "errorDescription",
              "validatedURL",
              "isMainFrame",
              "frameProcessId",
              "frameRoutingId"
            ]);
          },
          "plugin-crashed": ({ args }) => {
            return this.arrayToObject(args, ["name", "version"]);
          },
          "preload-error": ({ args }) => {
            return this.arrayToObject(args, ["preloadPath", "error"]);
          }
        }
      };
      events = {
        app: {
          "certificate-error": true,
          "child-process-gone": true,
          "render-process-gone": true
        },
        webContents: {
          // 'console-message': true,
          "did-fail-load": true,
          "did-fail-provisional-load": true,
          "plugin-crashed": true,
          "preload-error": true,
          "unresponsive": true
        }
      };
      externalApi = void 0;
      level = "error";
      scope = "";
      constructor(options = {}) {
        this.setOptions(options);
      }
      setOptions({
        events,
        externalApi,
        level,
        logger,
        format,
        formatters,
        scope
      }) {
        if (typeof events === "object") {
          this.events = events;
        }
        if (typeof externalApi === "object") {
          this.externalApi = externalApi;
        }
        if (typeof level === "string") {
          this.level = level;
        }
        if (typeof logger === "object") {
          this.logger = logger;
        }
        if (typeof format === "string" || typeof format === "function") {
          this.format = format;
        }
        if (typeof formatters === "object") {
          this.formatters = formatters;
        }
        if (typeof scope === "string") {
          this.scope = scope;
        }
      }
      startLogging(options = {}) {
        this.setOptions(options);
        this.disposeListeners();
        for (const eventName of this.getEventNames(this.events.app)) {
          this.disposers.push(
            this.externalApi.onAppEvent(eventName, (...handlerArgs) => {
              this.handleEvent({ eventSource: "app", eventName, handlerArgs });
            })
          );
        }
        for (const eventName of this.getEventNames(this.events.webContents)) {
          this.disposers.push(
            this.externalApi.onEveryWebContentsEvent(
              eventName,
              (...handlerArgs) => {
                this.handleEvent(
                  { eventSource: "webContents", eventName, handlerArgs }
                );
              }
            )
          );
        }
      }
      stopLogging() {
        this.disposeListeners();
      }
      arrayToObject(array, fieldNames) {
        const obj = {};
        fieldNames.forEach((fieldName, index) => {
          obj[fieldName] = array[index];
        });
        if (array.length > fieldNames.length) {
          obj.unknownArgs = array.slice(fieldNames.length);
        }
        return obj;
      }
      disposeListeners() {
        this.disposers.forEach((disposer) => disposer());
        this.disposers = [];
      }
      formatEventLog({ eventName, eventSource, handlerArgs }) {
        const [event, ...args] = handlerArgs;
        if (typeof this.format === "function") {
          return this.format({ args, event, eventName, eventSource });
        }
        const formatter = this.formatters[eventSource]?.[eventName];
        let formattedArgs = args;
        if (typeof formatter === "function") {
          formattedArgs = formatter({ args, event, eventName, eventSource });
        }
        if (!formattedArgs) {
          return void 0;
        }
        const eventData = {};
        if (Array.isArray(formattedArgs)) {
          eventData.args = formattedArgs;
        } else if (typeof formattedArgs === "object") {
          Object.assign(eventData, formattedArgs);
        }
        if (eventSource === "webContents") {
          Object.assign(eventData, this.getWebContentsDetails(event?.sender));
        }
        const title = this.format.replace("{eventSource}", eventSource === "app" ? "App" : "WebContents").replace("{eventName}", eventName);
        return [title, eventData];
      }
      getEventNames(eventMap) {
        if (!eventMap || typeof eventMap !== "object") {
          return [];
        }
        return Object.entries(eventMap).filter(([_, listen]) => listen).map(([eventName]) => eventName);
      }
      getWebContentsDetails(webContents) {
        if (!webContents?.loadURL) {
          return {};
        }
        try {
          return {
            webContents: {
              id: webContents.id,
              url: webContents.getURL()
            }
          };
        } catch {
          return {};
        }
      }
      handleEvent({ eventName, eventSource, handlerArgs }) {
        const log2 = this.formatEventLog({ eventName, eventSource, handlerArgs });
        if (log2) {
          const logFns = this.scope ? this.logger.scope(this.scope) : this.logger;
          logFns?.[this.level]?.(...log2);
        }
      }
    };
    module2.exports = EventLogger;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/transforms/format.js
var require_format = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/transforms/format.js"(exports2, module2) {
    "use strict";
    var { transform } = require_transform();
    module2.exports = {
      concatFirstStringElements,
      formatScope,
      formatText,
      formatVariables,
      timeZoneFromOffset,
      format({ message, logger, transport, data = message?.data }) {
        switch (typeof transport.format) {
          case "string": {
            return transform({
              message,
              logger,
              transforms: [formatVariables, formatScope, formatText],
              transport,
              initialData: [transport.format, ...data]
            });
          }
          case "function": {
            return transport.format({
              data,
              level: message?.level || "info",
              logger,
              message,
              transport
            });
          }
          default: {
            return data;
          }
        }
      }
    };
    function concatFirstStringElements({ data }) {
      if (typeof data[0] !== "string" || typeof data[1] !== "string") {
        return data;
      }
      if (data[0].match(/%[1cdfiOos]/)) {
        return data;
      }
      return [`${data[0]} ${data[1]}`, ...data.slice(2)];
    }
    function timeZoneFromOffset(minutesOffset) {
      const minutesPositive = Math.abs(minutesOffset);
      const sign = minutesOffset > 0 ? "-" : "+";
      const hours = Math.floor(minutesPositive / 60).toString().padStart(2, "0");
      const minutes = (minutesPositive % 60).toString().padStart(2, "0");
      return `${sign}${hours}:${minutes}`;
    }
    function formatScope({ data, logger, message }) {
      const { defaultLabel, labelLength } = logger?.scope || {};
      const template = data[0];
      let label = message.scope;
      if (!label) {
        label = defaultLabel;
      }
      let scopeText;
      if (label === "") {
        scopeText = labelLength > 0 ? "".padEnd(labelLength + 3) : "";
      } else if (typeof label === "string") {
        scopeText = ` (${label})`.padEnd(labelLength + 3);
      } else {
        scopeText = "";
      }
      data[0] = template.replace("{scope}", scopeText);
      return data;
    }
    function formatVariables({ data, message }) {
      let template = data[0];
      if (typeof template !== "string") {
        return data;
      }
      template = template.replace("{level}]", `${message.level}]`.padEnd(6, " "));
      const date = message.date || /* @__PURE__ */ new Date();
      data[0] = template.replace(/\{(\w+)}/g, (substring, name) => {
        switch (name) {
          case "level":
            return message.level || "info";
          case "logId":
            return message.logId;
          case "y":
            return date.getFullYear().toString(10);
          case "m":
            return (date.getMonth() + 1).toString(10).padStart(2, "0");
          case "d":
            return date.getDate().toString(10).padStart(2, "0");
          case "h":
            return date.getHours().toString(10).padStart(2, "0");
          case "i":
            return date.getMinutes().toString(10).padStart(2, "0");
          case "s":
            return date.getSeconds().toString(10).padStart(2, "0");
          case "ms":
            return date.getMilliseconds().toString(10).padStart(3, "0");
          case "z":
            return timeZoneFromOffset(date.getTimezoneOffset());
          case "iso":
            return date.toISOString();
          default: {
            return message.variables?.[name] || substring;
          }
        }
      }).trim();
      return data;
    }
    function formatText({ data }) {
      const template = data[0];
      if (typeof template !== "string") {
        return data;
      }
      const textTplPosition = template.lastIndexOf("{text}");
      if (textTplPosition === template.length - 6) {
        data[0] = template.replace(/\s?{text}/, "");
        if (data[0] === "") {
          data.shift();
        }
        return data;
      }
      const templatePieces = template.split("{text}");
      let result = [];
      if (templatePieces[0] !== "") {
        result.push(templatePieces[0]);
      }
      result = result.concat(data.slice(1));
      if (templatePieces[1] !== "") {
        result.push(templatePieces[1]);
      }
      return result;
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transforms/object.js
var require_object = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transforms/object.js"(exports2, module2) {
    "use strict";
    var util = require("util");
    module2.exports = {
      serialize,
      maxDepth({ data, transport, depth = transport?.depth ?? 6 }) {
        if (!data) {
          return data;
        }
        if (depth < 1) {
          if (Array.isArray(data)) return "[array]";
          if (typeof data === "object" && data) return "[object]";
          return data;
        }
        if (Array.isArray(data)) {
          return data.map((child) => module2.exports.maxDepth({
            data: child,
            depth: depth - 1
          }));
        }
        if (typeof data !== "object") {
          return data;
        }
        if (data && typeof data.toISOString === "function") {
          return data;
        }
        if (data === null) {
          return null;
        }
        if (data instanceof Error) {
          return data;
        }
        const newJson = {};
        for (const i in data) {
          if (!Object.prototype.hasOwnProperty.call(data, i)) continue;
          newJson[i] = module2.exports.maxDepth({
            data: data[i],
            depth: depth - 1
          });
        }
        return newJson;
      },
      toJSON({ data }) {
        return JSON.parse(JSON.stringify(data, createSerializer()));
      },
      toString({ data, transport }) {
        const inspectOptions = transport?.inspectOptions || {};
        const simplifiedData = data.map((item) => {
          if (item === void 0) {
            return void 0;
          }
          try {
            const str = JSON.stringify(item, createSerializer(), "  ");
            return str === void 0 ? void 0 : JSON.parse(str);
          } catch (e) {
            return item;
          }
        });
        return util.formatWithOptions(inspectOptions, ...simplifiedData);
      }
    };
    function createSerializer(options = {}) {
      const seen = /* @__PURE__ */ new WeakSet();
      return function(key, value) {
        if (typeof value === "object" && value !== null) {
          if (seen.has(value)) {
            return void 0;
          }
          seen.add(value);
        }
        return serialize(key, value, options);
      };
    }
    function serialize(key, value, options = {}) {
      const serializeMapAndSet = options?.serializeMapAndSet !== false;
      if (value instanceof Error) {
        return value.stack;
      }
      if (!value) {
        return value;
      }
      if (typeof value === "function") {
        return `[function] ${value.toString()}`;
      }
      if (value instanceof Date) {
        return value.toISOString();
      }
      if (serializeMapAndSet && value instanceof Map && Object.fromEntries) {
        return Object.fromEntries(value);
      }
      if (serializeMapAndSet && value instanceof Set && Array.from) {
        return Array.from(value);
      }
      return value;
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/transforms/style.js
var require_style = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/core/transforms/style.js"(exports2, module2) {
    "use strict";
    module2.exports = {
      transformStyles,
      applyAnsiStyles({ data }) {
        return transformStyles(data, styleToAnsi, resetAnsiStyle);
      },
      removeStyles({ data }) {
        return transformStyles(data, () => "");
      }
    };
    var ANSI_COLORS = {
      unset: "\x1B[0m",
      black: "\x1B[30m",
      red: "\x1B[31m",
      green: "\x1B[32m",
      yellow: "\x1B[33m",
      blue: "\x1B[34m",
      magenta: "\x1B[35m",
      cyan: "\x1B[36m",
      white: "\x1B[37m",
      gray: "\x1B[90m"
    };
    function styleToAnsi(style) {
      const color = style.replace(/color:\s*(\w+).*/, "$1").toLowerCase();
      return ANSI_COLORS[color] || "";
    }
    function resetAnsiStyle(string) {
      return string + ANSI_COLORS.unset;
    }
    function transformStyles(data, onStyleFound, onStyleApplied) {
      const foundStyles = {};
      return data.reduce((result, item, index, array) => {
        if (foundStyles[index]) {
          return result;
        }
        if (typeof item === "string") {
          let valueIndex = index;
          let styleApplied = false;
          item = item.replace(/%[1cdfiOos]/g, (match) => {
            valueIndex += 1;
            if (match !== "%c") {
              return match;
            }
            const style = array[valueIndex];
            if (typeof style === "string") {
              foundStyles[valueIndex] = true;
              styleApplied = true;
              return onStyleFound(style, item);
            }
            return match;
          });
          if (styleApplied && onStyleApplied) {
            item = onStyleApplied(item);
          }
        }
        result.push(item);
        return result;
      }, []);
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/console.js
var require_console2 = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/console.js"(exports2, module2) {
    "use strict";
    var {
      concatFirstStringElements,
      format
    } = require_format();
    var { maxDepth, toJSON } = require_object();
    var {
      applyAnsiStyles,
      removeStyles
    } = require_style();
    var { transform } = require_transform();
    var consoleMethods = {
      error: console.error,
      warn: console.warn,
      info: console.info,
      verbose: console.info,
      debug: console.debug,
      silly: console.debug,
      log: console.log
    };
    module2.exports = consoleTransportFactory;
    var separator = process.platform === "win32" ? ">" : "\u203A";
    var DEFAULT_FORMAT = `%c{h}:{i}:{s}.{ms}{scope}%c ${separator} {text}`;
    Object.assign(consoleTransportFactory, {
      DEFAULT_FORMAT
    });
    function consoleTransportFactory(logger) {
      return Object.assign(transport, {
        colorMap: {
          error: "red",
          warn: "yellow",
          info: "cyan",
          verbose: "unset",
          debug: "gray",
          silly: "gray",
          default: "unset"
        },
        format: DEFAULT_FORMAT,
        level: "silly",
        transforms: [
          addTemplateColors,
          format,
          formatStyles,
          concatFirstStringElements,
          maxDepth,
          toJSON
        ],
        useStyles: process.env.FORCE_STYLES,
        writeFn({ message }) {
          const consoleLogFn = consoleMethods[message.level] || consoleMethods.info;
          consoleLogFn(...message.data);
        }
      });
      function transport(message) {
        const data = transform({ logger, message, transport });
        transport.writeFn({
          message: { ...message, data }
        });
      }
    }
    function addTemplateColors({ data, message, transport }) {
      if (typeof transport.format !== "string" || !transport.format.includes("%c")) {
        return data;
      }
      return [
        `color:${levelToStyle(message.level, transport)}`,
        "color:unset",
        ...data
      ];
    }
    function canUseStyles(useStyleValue, level) {
      if (typeof useStyleValue === "boolean") {
        return useStyleValue;
      }
      const useStderr = level === "error" || level === "warn";
      const stream = useStderr ? process.stderr : process.stdout;
      return stream && stream.isTTY;
    }
    function formatStyles(args) {
      const { message, transport } = args;
      const useStyles = canUseStyles(transport.useStyles, message.level);
      const nextTransform = useStyles ? applyAnsiStyles : removeStyles;
      return nextTransform(args);
    }
    function levelToStyle(level, transport) {
      return transport.colorMap[level] || transport.colorMap.default;
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/File.js
var require_File = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/File.js"(exports2, module2) {
    "use strict";
    var EventEmitter = require("events");
    var fs2 = require("fs");
    var os = require("os");
    var File = class extends EventEmitter {
      asyncWriteQueue = [];
      bytesWritten = 0;
      hasActiveAsyncWriting = false;
      path = null;
      initialSize = void 0;
      writeOptions = null;
      writeAsync = false;
      constructor({
        path: path2,
        writeOptions = { encoding: "utf8", flag: "a", mode: 438 },
        writeAsync = false
      }) {
        super();
        this.path = path2;
        this.writeOptions = writeOptions;
        this.writeAsync = writeAsync;
      }
      get size() {
        return this.getSize();
      }
      clear() {
        try {
          fs2.writeFileSync(this.path, "", {
            mode: this.writeOptions.mode,
            flag: "w"
          });
          this.reset();
          return true;
        } catch (e) {
          if (e.code === "ENOENT") {
            return true;
          }
          this.emit("error", e, this);
          return false;
        }
      }
      crop(bytesAfter) {
        try {
          const content = readFileSyncFromEnd(this.path, bytesAfter || 4096);
          this.clear();
          this.writeLine(`[log cropped]${os.EOL}${content}`);
        } catch (e) {
          this.emit(
            "error",
            new Error(`Couldn't crop file ${this.path}. ${e.message}`),
            this
          );
        }
      }
      getSize() {
        if (this.initialSize === void 0) {
          try {
            const stats = fs2.statSync(this.path);
            this.initialSize = stats.size;
          } catch (e) {
            this.initialSize = 0;
          }
        }
        return this.initialSize + this.bytesWritten;
      }
      increaseBytesWrittenCounter(text) {
        this.bytesWritten += Buffer.byteLength(text, this.writeOptions.encoding);
      }
      isNull() {
        return false;
      }
      nextAsyncWrite() {
        const file = this;
        if (this.hasActiveAsyncWriting || this.asyncWriteQueue.length === 0) {
          return;
        }
        const text = this.asyncWriteQueue.join("");
        this.asyncWriteQueue = [];
        this.hasActiveAsyncWriting = true;
        fs2.writeFile(this.path, text, this.writeOptions, (e) => {
          file.hasActiveAsyncWriting = false;
          if (e) {
            file.emit(
              "error",
              new Error(`Couldn't write to ${file.path}. ${e.message}`),
              this
            );
          } else {
            file.increaseBytesWrittenCounter(text);
          }
          file.nextAsyncWrite();
        });
      }
      reset() {
        this.initialSize = void 0;
        this.bytesWritten = 0;
      }
      toString() {
        return this.path;
      }
      writeLine(text) {
        text += os.EOL;
        if (this.writeAsync) {
          this.asyncWriteQueue.push(text);
          this.nextAsyncWrite();
          return;
        }
        try {
          fs2.writeFileSync(this.path, text, this.writeOptions);
          this.increaseBytesWrittenCounter(text);
        } catch (e) {
          this.emit(
            "error",
            new Error(`Couldn't write to ${this.path}. ${e.message}`),
            this
          );
        }
      }
    };
    module2.exports = File;
    function readFileSyncFromEnd(filePath, bytesCount) {
      const buffer = Buffer.alloc(bytesCount);
      const stats = fs2.statSync(filePath);
      const readLength = Math.min(stats.size, bytesCount);
      const offset = Math.max(0, stats.size - bytesCount);
      const fd = fs2.openSync(filePath, "r");
      const totalBytes = fs2.readSync(fd, buffer, 0, readLength, offset);
      fs2.closeSync(fd);
      return buffer.toString("utf8", 0, totalBytes);
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/NullFile.js
var require_NullFile = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/NullFile.js"(exports2, module2) {
    "use strict";
    var File = require_File();
    var NullFile = class extends File {
      clear() {
      }
      crop() {
      }
      getSize() {
        return 0;
      }
      isNull() {
        return true;
      }
      writeLine() {
      }
    };
    module2.exports = NullFile;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/FileRegistry.js
var require_FileRegistry = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/FileRegistry.js"(exports2, module2) {
    "use strict";
    var EventEmitter = require("events");
    var fs2 = require("fs");
    var path2 = require("path");
    var File = require_File();
    var NullFile = require_NullFile();
    var FileRegistry = class extends EventEmitter {
      store = {};
      constructor() {
        super();
        this.emitError = this.emitError.bind(this);
      }
      /**
       * Provide a File object corresponding to the filePath
       * @param {string} filePath
       * @param {WriteOptions} [writeOptions]
       * @param {boolean} [writeAsync]
       * @return {File}
       */
      provide({ filePath, writeOptions = {}, writeAsync = false }) {
        let file;
        try {
          filePath = path2.resolve(filePath);
          if (this.store[filePath]) {
            return this.store[filePath];
          }
          file = this.createFile({ filePath, writeOptions, writeAsync });
        } catch (e) {
          file = new NullFile({ path: filePath });
          this.emitError(e, file);
        }
        file.on("error", this.emitError);
        this.store[filePath] = file;
        return file;
      }
      /**
       * @param {string} filePath
       * @param {WriteOptions} writeOptions
       * @param {boolean} async
       * @return {File}
       * @private
       */
      createFile({ filePath, writeOptions, writeAsync }) {
        this.testFileWriting({ filePath, writeOptions });
        return new File({ path: filePath, writeOptions, writeAsync });
      }
      /**
       * @param {Error} error
       * @param {File} file
       * @private
       */
      emitError(error, file) {
        this.emit("error", error, file);
      }
      /**
       * @param {string} filePath
       * @param {WriteOptions} writeOptions
       * @private
       */
      testFileWriting({ filePath, writeOptions }) {
        fs2.mkdirSync(path2.dirname(filePath), { recursive: true });
        fs2.writeFileSync(filePath, "", { flag: "a", mode: writeOptions.mode });
      }
    };
    module2.exports = FileRegistry;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/index.js
var require_file = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/file/index.js"(exports2, module2) {
    "use strict";
    var fs2 = require("fs");
    var os = require("os");
    var path2 = require("path");
    var FileRegistry = require_FileRegistry();
    var { transform } = require_transform();
    var { removeStyles } = require_style();
    var {
      format,
      concatFirstStringElements
    } = require_format();
    var { toString } = require_object();
    module2.exports = fileTransportFactory;
    var globalRegistry = new FileRegistry();
    function fileTransportFactory(logger, { registry = globalRegistry, externalApi } = {}) {
      let pathVariables;
      if (registry.listenerCount("error") < 1) {
        registry.on("error", (e, file) => {
          logConsole(`Can't write to ${file}`, e);
        });
      }
      return Object.assign(transport, {
        fileName: getDefaultFileName(logger.variables.processType),
        format: "[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}]{scope} {text}",
        getFile,
        inspectOptions: { depth: 5 },
        level: "silly",
        maxSize: 1024 ** 2,
        readAllLogs,
        sync: true,
        transforms: [removeStyles, format, concatFirstStringElements, toString],
        writeOptions: { flag: "a", mode: 438, encoding: "utf8" },
        archiveLogFn(file) {
          const oldPath = file.toString();
          const inf = path2.parse(oldPath);
          try {
            fs2.renameSync(oldPath, path2.join(inf.dir, `${inf.name}.old${inf.ext}`));
          } catch (e) {
            logConsole("Could not rotate log", e);
            const quarterOfMaxSize = Math.round(transport.maxSize / 4);
            file.crop(Math.min(quarterOfMaxSize, 256 * 1024));
          }
        },
        resolvePathFn(vars) {
          return path2.join(vars.libraryDefaultDir, vars.fileName);
        },
        setAppName(name) {
          logger.dependencies.externalApi.setAppName(name);
        }
      });
      function transport(message) {
        const file = getFile(message);
        const needLogRotation = transport.maxSize > 0 && file.size > transport.maxSize;
        if (needLogRotation) {
          transport.archiveLogFn(file);
          file.reset();
        }
        const content = transform({ logger, message, transport });
        file.writeLine(content);
      }
      function initializeOnFirstAccess() {
        if (pathVariables) {
          return;
        }
        pathVariables = Object.create(
          Object.prototype,
          {
            ...Object.getOwnPropertyDescriptors(
              externalApi.getPathVariables()
            ),
            fileName: {
              get() {
                return transport.fileName;
              },
              enumerable: true
            }
          }
        );
        if (typeof transport.archiveLog === "function") {
          transport.archiveLogFn = transport.archiveLog;
          logConsole("archiveLog is deprecated. Use archiveLogFn instead");
        }
        if (typeof transport.resolvePath === "function") {
          transport.resolvePathFn = transport.resolvePath;
          logConsole("resolvePath is deprecated. Use resolvePathFn instead");
        }
      }
      function logConsole(message, error = null, level = "error") {
        const data = [`electron-log.transports.file: ${message}`];
        if (error) {
          data.push(error);
        }
        logger.transports.console({ data, date: /* @__PURE__ */ new Date(), level });
      }
      function getFile(msg) {
        initializeOnFirstAccess();
        const filePath = transport.resolvePathFn(pathVariables, msg);
        return registry.provide({
          filePath,
          writeAsync: !transport.sync,
          writeOptions: transport.writeOptions
        });
      }
      function readAllLogs({ fileFilter = (f) => f.endsWith(".log") } = {}) {
        initializeOnFirstAccess();
        const logsPath = path2.dirname(transport.resolvePathFn(pathVariables));
        if (!fs2.existsSync(logsPath)) {
          return [];
        }
        return fs2.readdirSync(logsPath).map((fileName) => path2.join(logsPath, fileName)).filter(fileFilter).map((logPath) => {
          try {
            return {
              path: logPath,
              lines: fs2.readFileSync(logPath, "utf8").split(os.EOL)
            };
          } catch {
            return null;
          }
        }).filter(Boolean);
      }
    }
    function getDefaultFileName(processType = process.type) {
      switch (processType) {
        case "renderer":
          return "renderer.log";
        case "worker":
          return "worker.log";
        default:
          return "main.log";
      }
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/ipc.js
var require_ipc2 = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/ipc.js"(exports2, module2) {
    "use strict";
    var { maxDepth, toJSON } = require_object();
    var { transform } = require_transform();
    module2.exports = ipcTransportFactory;
    function ipcTransportFactory(logger, { externalApi }) {
      Object.assign(transport, {
        depth: 3,
        eventId: "__ELECTRON_LOG_IPC__",
        level: logger.isDev ? "silly" : false,
        transforms: [toJSON, maxDepth]
      });
      return externalApi?.isElectron() ? transport : void 0;
      function transport(message) {
        if (message?.variables?.processType === "renderer") {
          return;
        }
        externalApi?.sendIpc(transport.eventId, {
          ...message,
          data: transform({ logger, message, transport })
        });
      }
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/remote.js
var require_remote = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/transports/remote.js"(exports2, module2) {
    "use strict";
    var http = require("http");
    var https = require("https");
    var { transform } = require_transform();
    var { removeStyles } = require_style();
    var { toJSON, maxDepth } = require_object();
    module2.exports = remoteTransportFactory;
    function remoteTransportFactory(logger) {
      return Object.assign(transport, {
        client: { name: "electron-application" },
        depth: 6,
        level: false,
        requestOptions: {},
        transforms: [removeStyles, toJSON, maxDepth],
        makeBodyFn({ message }) {
          return JSON.stringify({
            client: transport.client,
            data: message.data,
            date: message.date.getTime(),
            level: message.level,
            scope: message.scope,
            variables: message.variables
          });
        },
        processErrorFn({ error }) {
          logger.processMessage(
            {
              data: [`electron-log: can't POST ${transport.url}`, error],
              level: "warn"
            },
            { transports: ["console", "file"] }
          );
        },
        sendRequestFn({ serverUrl, requestOptions, body }) {
          const httpTransport = serverUrl.startsWith("https:") ? https : http;
          const request = httpTransport.request(serverUrl, {
            method: "POST",
            ...requestOptions,
            headers: {
              "Content-Type": "application/json",
              "Content-Length": body.length,
              ...requestOptions.headers
            }
          });
          request.write(body);
          request.end();
          return request;
        }
      });
      function transport(message) {
        if (!transport.url) {
          return;
        }
        const body = transport.makeBodyFn({
          logger,
          message: { ...message, data: transform({ logger, message, transport }) },
          transport
        });
        const request = transport.sendRequestFn({
          serverUrl: transport.url,
          requestOptions: transport.requestOptions,
          body: Buffer.from(body, "utf8")
        });
        request.on("error", (error) => transport.processErrorFn({
          error,
          logger,
          message,
          request,
          transport
        }));
      }
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/createDefaultLogger.js
var require_createDefaultLogger = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/createDefaultLogger.js"(exports2, module2) {
    "use strict";
    var Logger = require_Logger();
    var ErrorHandler = require_ErrorHandler();
    var EventLogger = require_EventLogger();
    var transportConsole = require_console2();
    var transportFile = require_file();
    var transportIpc = require_ipc2();
    var transportRemote = require_remote();
    module2.exports = createDefaultLogger;
    function createDefaultLogger({ dependencies, initializeFn }) {
      const defaultLogger = new Logger({
        dependencies,
        errorHandler: new ErrorHandler(),
        eventLogger: new EventLogger(),
        initializeFn,
        isDev: dependencies.externalApi?.isDev(),
        logId: "default",
        transportFactories: {
          console: transportConsole,
          file: transportFile,
          ipc: transportIpc,
          remote: transportRemote
        },
        variables: {
          processType: "main"
        }
      });
      defaultLogger.default = defaultLogger;
      defaultLogger.Logger = Logger;
      defaultLogger.processInternalErrorFn = (e) => {
        defaultLogger.transports.console.writeFn({
          message: {
            data: ["Unhandled electron-log error", e],
            level: "error"
          }
        });
      };
      return defaultLogger;
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/main/index.js
var require_main = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/main/index.js"(exports2, module2) {
    "use strict";
    var electron = require("electron");
    var ElectronExternalApi = require_ElectronExternalApi();
    var { initialize } = require_initialize();
    var createDefaultLogger = require_createDefaultLogger();
    var externalApi = new ElectronExternalApi({ electron });
    var defaultLogger = createDefaultLogger({
      dependencies: { externalApi },
      initializeFn: initialize
    });
    module2.exports = defaultLogger;
    externalApi.onIpc("__ELECTRON_LOG__", (_, message) => {
      if (message.scope) {
        defaultLogger.Logger.getInstance(message).scope(message.scope);
      }
      const date = new Date(message.date);
      processMessage({
        ...message,
        date: date.getTime() ? date : /* @__PURE__ */ new Date()
      });
    });
    externalApi.onIpcInvoke("__ELECTRON_LOG__", (_, { cmd = "", logId }) => {
      switch (cmd) {
        case "getOptions": {
          const logger = defaultLogger.Logger.getInstance({ logId });
          return {
            levels: logger.levels,
            logId
          };
        }
        default: {
          processMessage({ data: [`Unknown cmd '${cmd}'`], level: "error" });
          return {};
        }
      }
    });
    function processMessage(message) {
      defaultLogger.Logger.getInstance(message)?.processMessage(message);
    }
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/index.js
var require_node = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/node/index.js"(exports2, module2) {
    "use strict";
    var NodeExternalApi = require_NodeExternalApi();
    var createDefaultLogger = require_createDefaultLogger();
    var externalApi = new NodeExternalApi();
    var defaultLogger = createDefaultLogger({
      dependencies: { externalApi }
    });
    module2.exports = defaultLogger;
  }
});

// ../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/index.js
var require_src = __commonJS({
  "../../node_modules/.pnpm/electron-log@5.4.4/node_modules/electron-log/src/index.js"(exports2, module2) {
    "use strict";
    var isRenderer = typeof process === "undefined" || (process.type === "renderer" || process.type === "worker");
    var isMain = typeof process === "object" && process.type === "browser";
    if (isRenderer) {
      require_electron_log_preload();
      module2.exports = require_renderer();
    } else if (isMain) {
      module2.exports = require_main();
    } else {
      module2.exports = require_node();
    }
  }
});

// electron/main.ts
var import_electron = require("electron");
var import_path = __toESM(require("path"), 1);
var import_fs = __toESM(require("fs"), 1);
var import_child_process = require("child_process");
var import_auto_launch = __toESM(require_dist(), 1);
var import_electron_log = __toESM(require_src(), 1);
var isDev = process.env.NODE_ENV === "development" || !import_electron.app.isPackaged;
var DEV_RENDERER_URL = "http://localhost:21098";
var CONFIG_PATH = import_path.default.join(import_electron.app.getPath("userData"), "axiom-config.json");
var ICON_PATH = import_path.default.join(__dirname, "..", "icons", "tray-icon.png");
var DEFAULT_CONFIG = {
  width: 1200,
  height: 750,
  pinned: false,
  hotkey: "CommandOrControl+Shift+Space",
  launchAtLogin: false,
  startMinimized: false,
  dismissOnBlur: false
};
function loadConfig() {
  try {
    if (import_fs.default.existsSync(CONFIG_PATH)) {
      const raw = import_fs.default.readFileSync(CONFIG_PATH, "utf-8");
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
    }
  } catch (e) {
    import_electron_log.default.warn("Failed to load config, using defaults:", e);
  }
  return { ...DEFAULT_CONFIG };
}
function saveConfig(config2) {
  const current = loadConfig();
  try {
    import_fs.default.writeFileSync(CONFIG_PATH, JSON.stringify({ ...current, ...config2 }, null, 2));
  } catch (e) {
    import_electron_log.default.error("Failed to save config:", e);
  }
}
var mainWindow = null;
var tray = null;
var config = loadConfig();
var isQuitting = false;
var apiServerProcess = null;
var autoLauncher = new import_auto_launch.default({
  name: "AXIOM",
  isHidden: true
});
function startApiServer() {
  if (isDev) return;
  const serverPath = import_path.default.join(process.resourcesPath, "api-server", "dist", "index.mjs");
  if (!import_fs.default.existsSync(serverPath)) {
    import_electron_log.default.warn("API server binary not found at:", serverPath);
    return;
  }
  apiServerProcess = (0, import_child_process.spawn)(process.execPath, [serverPath], {
    env: {
      ...process.env,
      NODE_ENV: "production",
      PORT: "8080"
    },
    detached: false,
    stdio: ["ignore", "pipe", "pipe"]
  });
  apiServerProcess.stdout?.on("data", (d) => import_electron_log.default.info("[api]", d.toString().trim()));
  apiServerProcess.stderr?.on("data", (d) => import_electron_log.default.warn("[api]", d.toString().trim()));
  apiServerProcess.on("exit", (code) => {
    import_electron_log.default.info(`API server exited with code ${code}`);
    apiServerProcess = null;
  });
}
function createWindow() {
  const display = import_electron.screen.getPrimaryDisplay();
  const { width: dw, height: dh } = display.workAreaSize;
  const x = config.x ?? Math.round((dw - config.width) / 2);
  const y = config.y ?? Math.round((dh - config.height) / 2);
  const win = new import_electron.BrowserWindow({
    x,
    y,
    width: config.width,
    height: config.height,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    transparent: true,
    vibrancy: "under-window",
    visualEffectState: "followWindow",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 14, y: 14 },
    show: false,
    alwaysOnTop: config.pinned,
    hasShadow: true,
    roundedCorners: true,
    webPreferences: {
      preload: import_path.default.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webSecurity: true
    }
  });
  if (isDev) {
    win.loadURL(DEV_RENDERER_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(import_path.default.join(__dirname, "..", "dist", "public", "index.html"));
  }
  win.once("ready-to-show", () => {
    if (!config.startMinimized) {
      win.show();
      win.focus();
    }
  });
  win.on("resize", () => {
    const [w, h] = win.getSize();
    saveConfig({ width: w, height: h });
  });
  win.on("moved", () => {
    const [px, py] = win.getPosition();
    saveConfig({ x: px, y: py });
  });
  win.on("blur", () => {
    if (config.dismissOnBlur && !config.pinned && !isQuitting) {
      win.hide();
    }
  });
  win.on("close", (e) => {
    if (!isQuitting) {
      e.preventDefault();
      win.hide();
    }
  });
  return win;
}
function createTray(win) {
  const iconExists = import_fs.default.existsSync(ICON_PATH);
  const icon = iconExists ? import_electron.nativeImage.createFromPath(ICON_PATH).resize({ width: 16, height: 16 }) : import_electron.nativeImage.createEmpty();
  const t = new import_electron.Tray(icon);
  t.setToolTip("AXIOM \u2014 AI Assistant");
  const buildMenu = () => import_electron.Menu.buildFromTemplate([
    {
      label: win.isVisible() ? "Hide AXIOM" : "Show AXIOM",
      click: () => toggleWindow(win)
    },
    { type: "separator" },
    {
      label: "Open Settings",
      click: () => {
        showWindow(win);
        win.webContents.send("navigate", "/settings");
      }
    },
    { type: "separator" },
    {
      label: "Quit AXIOM",
      accelerator: "CommandOrControl+Q",
      click: () => {
        isQuitting = true;
        import_electron.app.quit();
      }
    }
  ]);
  t.on("double-click", () => toggleWindow(win));
  t.on("click", () => {
    if (process.platform === "win32") toggleWindow(win);
  });
  t.on("right-click", () => t.popUpContextMenu(buildMenu()));
  win.on("show", () => t.setContextMenu(buildMenu()));
  win.on("hide", () => t.setContextMenu(buildMenu()));
  t.setContextMenu(buildMenu());
  return t;
}
function showWindow(win) {
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
}
function toggleWindow(win) {
  if (win.isVisible() && win.isFocused()) {
    win.hide();
  } else {
    showWindow(win);
  }
}
function registerHotkey(accelerator, win) {
  import_electron.globalShortcut.unregisterAll();
  try {
    const ok = import_electron.globalShortcut.register(accelerator, () => {
      toggleWindow(win);
      win.webContents.send("hotkey-triggered");
    });
    if (!ok) import_electron_log.default.warn("Hotkey registration failed:", accelerator);
    return ok;
  } catch (e) {
    import_electron_log.default.error("Hotkey error:", e);
    return false;
  }
}
function setupIpc(win) {
  import_electron.ipcMain.handle("window:toggle", () => toggleWindow(win));
  import_electron.ipcMain.handle("window:show", () => showWindow(win));
  import_electron.ipcMain.handle("window:hide", () => win.hide());
  import_electron.ipcMain.handle("window:minimize", () => win.minimize());
  import_electron.ipcMain.handle("window:set-pin", (_e, pinned) => {
    config.pinned = pinned;
    win.setAlwaysOnTop(pinned, "floating");
    saveConfig({ pinned });
    win.webContents.send("pin-changed", pinned);
  });
  import_electron.ipcMain.handle("window:set-dismiss-on-blur", (_e, enabled) => {
    config.dismissOnBlur = enabled;
    saveConfig({ dismissOnBlur: enabled });
  });
  import_electron.ipcMain.handle("hotkey:update", (_e, accelerator) => {
    const ok = registerHotkey(accelerator, win);
    if (ok) {
      config.hotkey = accelerator;
      saveConfig({ hotkey: accelerator });
    }
    return { success: ok };
  });
  import_electron.ipcMain.handle("autolaunch:set", async (_e, enabled) => {
    try {
      if (enabled) {
        await autoLauncher.enable();
      } else {
        await autoLauncher.disable();
      }
      config.launchAtLogin = enabled;
      saveConfig({ launchAtLogin: enabled });
      return { success: true };
    } catch (e) {
      import_electron_log.default.error("AutoLaunch error:", e);
      return { success: false, error: String(e) };
    }
  });
  import_electron.ipcMain.handle("autolaunch:is-enabled", async () => {
    try {
      return await autoLauncher.isEnabled();
    } catch {
      return false;
    }
  });
  import_electron.ipcMain.handle("app:get-config", () => loadConfig());
  import_electron.ipcMain.handle("app:get-version", () => import_electron.app.getVersion());
  import_electron.ipcMain.handle("app:open-external", (_e, url) => {
    import_electron.shell.openExternal(url);
  });
  import_electron.ipcMain.handle("app:show-item-in-folder", (_e, filePath) => {
    import_electron.shell.showItemInFolder(filePath);
  });
  import_electron.ipcMain.handle("dialog:open-directory", async () => {
    const result = await import_electron.dialog.showOpenDialog(win, {
      properties: ["openDirectory", "createDirectory"],
      title: "Select an allowed directory for AXIOM"
    });
    return result.canceled ? null : result.filePaths[0];
  });
  import_electron.ipcMain.handle("platform:get", () => process.platform);
}
import_electron.app.whenReady().then(() => {
  import_electron_log.default.info("AXIOM starting\u2026");
  startApiServer();
  mainWindow = createWindow();
  tray = createTray(mainWindow);
  setupIpc(mainWindow);
  registerHotkey(config.hotkey, mainWindow);
  import_electron.app.on("activate", () => {
    if (mainWindow) showWindow(mainWindow);
  });
});
import_electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") import_electron.app.quit();
});
import_electron.app.on("before-quit", () => {
  isQuitting = true;
  import_electron.globalShortcut.unregisterAll();
  if (apiServerProcess) {
    apiServerProcess.kill("SIGTERM");
    apiServerProcess = null;
  }
});
import_electron.app.on("will-quit", () => {
  import_electron.globalShortcut.unregisterAll();
});
var gotLock = import_electron.app.requestSingleInstanceLock();
if (!gotLock) {
  import_electron.app.quit();
} else {
  import_electron.app.on("second-instance", () => {
    if (mainWindow) showWindow(mainWindow);
  });
}
//# sourceMappingURL=main.js.map
