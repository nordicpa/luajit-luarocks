#!/usr/bin/env python3
# -- fmt: off
# fmt: off

import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NVIM = Path.home() / ".config/nvim"
LAZY = Path.home() / ".local/share/nvim/lazy/lazy.nvim"
PATCHES = Path.home() / ".local/share/nvim/lazy-origs"
FILES = {
    "lazy.lua": NVIM / "lua/config/lazy.lua",
    "rockspec.lua": LAZY / "lua/lazy/pkg/rockspec.lua",
    "config.lua": LAZY / "lua/lazy/core/config.lua",
    "git.lua": LAZY / "lua/lazy/manage/task/git.lua",
}

def lazy_config_patched(text):
    if shutil.which("luarocks-jit") is None:
        return text
    old = """\
  rocks = {
    enabled = false,
"""
    new = """\
  rocks = {
    enabled = true,
"""
    if new in text: return text
    if text.count(old) != 1:
        raise RuntimeError( f"lazy.lua: expected exactly one {old.strip()!r} occurrence")
    return text.replace(old, new)

def config_patched(text):
    old = 'server = "https://lumen-oss.github.io/rocks-binaries/",'
    new = 'server = "https://luarocks.org/",'
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError("config.lua: expected exactly one Lazy binary-rock server line")
    return text.replace(old, new)

# -- fmt: on
def rockspec_patched(text):
    patches = [
        ( 'root .. "/lib/luarocks/rocks-5.1/manifest"', 'root .. "/lib/luarocks/rocks-jit/manifest"'),
        ("  local env = {}\n", '  local env = { CXX = "g++ -fPIC" }\n'),
        (
            '  local luarocks = "luarocks"\n',
            """\
  local luarocks = "luarocks"
  if vim.fn.executable("luarocks-jit") == 1 then
    luarocks = "luarocks-jit"
  end
""",
        ),
        (
            '  local root = Config.options.rocks.root .. "/" .. task.plugin.name\n',
            """\
  local root = Config.options.rocks.root .. "/" .. task.plugin.name
  local lua_dir = vim.fn.system("luarocks-jit config"):match('LUA_DIR%s*=%s*"([^"]+)"')

  env.LUA_PATH = table.concat({
    root .. "/share/lua/5.1/?.lua",
    root .. "/share/lua/5.1/?/init.lua",
    lua_dir .. "/share/lua/jit/?.lua",
    lua_dir .. "/share/lua/jit/?/init.lua",
  }, ";")
""",
        ),
    ]
    for old, new in patches:
        if new.strip() in text:
            continue
        if text.count(old) != 1:
            raise RuntimeError(f"rockspec.lua: expected exactly one {old.strip()!r} occurrence")
        text = text.replace(old, new)
    return text

# fmt: off
def git_patched(text):
    marker = """\
            if line:gsub("[\\\\/]", "/") == "doc/tags" then
              local Process = require("lazy.manage.process")
              Process.exec({ "git", "checkout", "--", "doc/tags" }, { cwd = self.plugin.dir })
              return false
            end
"""
    addition = """\
            local path = line:gsub("[\\\\/]", "/")
"""
    filters = """\
            return line ~= ""
              and path ~= "lua/lazy/core/config.lua"
              and path ~= "lua/lazy/pkg/rockspec.lua"
              and path ~= "lua/lazy/manage/task/git.lua"
"""
    if addition.strip() in text:
        return text
    if text.count(marker) != 1:
        raise RuntimeError("git.lua: expected exactly one status-filter marker")
    old = marker + '            return line ~= ""\n'
    if text.count(old) != 1:
        raise RuntimeError("git.lua: expected exactly one original return statement")
    return text.replace(old, marker + addition + filters)

PATCHERS = {
    "lazy.lua": lazy_config_patched,
    "config.lua": config_patched,
    "rockspec.lua": rockspec_patched,
    "git.lua": git_patched,
}

def original_path(name):
    return PATCHES / f"{name}.orig"

def read(path):
    return path.read_text()

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

def patched_text(name, original):
    return PATCHERS[name](original)

def status_one(name, target):
    orig_path = original_path(name)
    if not orig_path.exists():
        return "NO-ORIG"
    original = read(orig_path)
    current = read(target)
    patched = patched_text(name, original)
    if current == patched:
        return "PATCHED"
    if current == original:
        return "UPSTREAM"
    return "DRIFT"

def apply():
    PATCHES.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, target in FILES.items():
        if not target.exists():
            print(f"ERROR: missing Lazy file: {target}")
            failed = True
            continue
        orig = original_path(name)
        current = read(target)
        if not orig.exists():
            print(f"{name}: first run — saving .orig")
            write(orig, current)
        original = read(orig)
        patched = patched_text(name, original)
        if current == patched:
            print(f"{name}: already patched")
            continue
        if current == original:
            write(target, patched)
            print(f"{name}: patched")
            continue
        print(f"ERROR: {name}: upstream drift detected")
        print("       current file matches neither .orig nor patched version")
        failed = True
    if failed:
        print()
        print("No .orig file was overwritten.")
        print("Inspect with:  lazy-patch.py --diff")
        print("Accept with:   lazy-patch.py --adopt")
        return 1
    return 0

def check():
    failed = False
    for name, target in FILES.items():
        state = status_one(name, target)
        print(f"{name}: {state}")
        if state in ("NO-ORIG", "DRIFT"):
            failed = True
    return 1 if failed else 0

def diff():
    for name, target in FILES.items():
        orig = original_path(name)
        if not orig.exists():
            print(f"### {name}: no .orig")
            continue
        a = read(orig).splitlines(True)
        b = read(target).splitlines(True)
        output = difflib.unified_diff(
            a,
            b,
            fromfile=str(orig),
            tofile=str(target),
        )
        print("".join(output), end="")

def restore():
    failed = False
    for name, target in FILES.items():
        orig = original_path(name)
        if not orig.exists():
            print(f"ERROR: {name}: no .orig")
            failed = True
            continue
        current = read(target)
        original = read(orig)
        patched = patched_text(name, original)
        if current not in (original, patched):
            print(f"ERROR: {name}: current file differs from both original and patched versions")
            failed = True
            continue
        write(target, original)
        print(f"{name}: restored")
    if failed: return 1
    for conf in (NVIM / "lua/plugins/neorg.lua",):
        if conf.exists():
            conf.unlink()
            print(f"{conf.name}: removed")
    for name in ("tree-sitter-norg", "tree-sitter-norg-meta"):
        path = Path.home() / ".local/share/nvim/lazy-rocks" / name
        if path.exists():
            shutil.rmtree(path)
            print(f"{name}: removed")
    return 0

def adopt():
    """
    Explicitly accept the current Lazy checkout as the new upstream base.
    Only files that differ from their existing .orig are replaced.
    """
    PATCHES.mkdir(parents=True, exist_ok=True)
    failed = False
    for name, target in FILES.items():
        if not target.exists():
            print(f"ERROR: missing Lazy file: {target}")
            failed = True
            continue
        orig = original_path(name)
        current = read(target)
        if orig.exists():
            old_original = read(orig)
            old_patched = patched_text(name, old_original)
            if current == old_patched:
                print(f"ERROR: {name}: currently patched; restore or update Lazy before --adopt")
                failed = True
                continue
            if current == old_original:
                print(f"{name}: unchanged upstream")
                continue
        write(orig, current)
        print(f"{name}: adopted new upstream")
    if failed:
        return 1
    return apply()

# fmt: off
def wipe_rocks(system=False):
    if system:
        if os.geteuid() != 0:
            raise SystemExit("--system requires root")
        paths = [Path("/root/.luarocks-jit"), Path("/usr/local/share/lua"), Path("/usr/local/lib/lua")]
    else:
        paths = [Path.home() / ".local/share/nvim/lazy-rocks", Path.home() / ".luarocks-jit"]
    for path in paths:
        if path.exists():
            print(f"WIPE {path}")
            shutil.rmtree(path)
        else:
            print(f"OK   {path}: absent")

NEORG_CONFIG = r"""return {
  "nvim-neorg/neorg",
  version = "*",
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-neorg/tree-sitter-norg",
    "nvim-neorg/tree-sitter-norg-meta",
  },
  -- build = ":Neorg sync-parsers",
  config = function(_, opts)
    local highlights = {
      ["@neorg.markup.bold.norg"]          = { link = "@markup.strong" },
      ["@neorg.markup.italic.norg"]        = { link = "@markup.italic" },
      ["@neorg.markup.strikethrough.norg"] = { link = "@markup.strikethrough" },
      ["@neorg.markup.underline.norg"]     = { link = "@markup.underline" },
      ["@neorg.markup.raw.norg"]           = { link = "String" },
    }
    for hl_group, style in pairs(highlights) do
      vim.api.nvim_set_hl(0, hl_group, style)
    end
    require("neorg").setup(opts)
  end,
}
"""

def test_config():
    write(NVIM / "lua/plugins/neorg.lua", NEORG_CONFIG)
    text = read(NVIM / "lua/plugins/neorg.lua")
    for dep in (
        '"nvim-neorg/tree-sitter-norg"',
        '"nvim-neorg/tree-sitter-norg-meta"',
    ):
        if dep not in text:
            raise RuntimeError(f"neorg.lua: missing dependency {dep}")
    print("neorg.lua: generated and verified")

def status():
    print(f"neorg.lua: {'present' if (NVIM / 'lua/plugins/neorg.lua').exists() else 'MISSING'}")
    for path in (
        Path.home() / ".local/share/nvim/lazy-rocks/tree-sitter-norg",
        Path.home() / ".local/share/nvim/lazy-rocks/tree-sitter-norg-meta",
    ):
        print(f"{path.name}: {'present' if path.exists() else 'MISSING'}")

TEST_LUA = r"""
local function fail(msg)
  vim.api.nvim_err_writeln("ERROR: " .. msg)
  vim.cmd("cquit 1")
end

print("test-run: nvim started")

if vim.fn.executable("luarocks-jit") ~= 1 then
  fail("luarocks-jit is not executable")
end
print("test-run: luarocks-jit available")

print("test-run: checking parser paths")

local function parser(lang)
  local path = package.searchpath("parser." .. lang, package.cpath)
  if not path then
    fail("parser." .. lang .. " not found in package.cpath")
  end
  print("parser." .. lang .. ": " .. path)
  return path
end

parser("norg")
parser("norg_meta")

print("test-run: checking parser registration")

if not vim._ts_has_language("norg") then
  fail("norg was not registered by Neorg")
end

print("test-run: norg registered")

if not vim._ts_has_language("norg_meta") then
  fail("norg_meta was not registered by Neorg")
end

print("test-run: norg_meta registered")

local testfile = vim.fn.expand("~/Downloads/test-ok.norg")

if vim.fn.filereadable(testfile) ~= 1 then
  fail("test file missing: " .. testfile)
end

print("test-run: opening test file")
vim.cmd("edit " .. vim.fn.fnameescape(testfile))

print("test-run: creating Tree-sitter parser")

local ok, parser_obj = pcall(vim.treesitter.get_parser, 0, "norg")
if not ok or not parser_obj then
  fail("Neorg Tree-sitter parser could not be created")
end

print("LuaRocks/Neorg integration: PASS")
vim.cmd("qa!")
"""

def test_run():
    if shutil.which("luarocks-jit") is None:
        raise RuntimeError("luarocks-jit not found")
    if shutil.which("nvim") is None:
        raise RuntimeError("nvim not found")
    neorg = NVIM / "lua/plugins/neorg.lua"
    if not neorg.exists():
        raise RuntimeError(f"missing Neorg config: {neorg}")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lua", delete=False) as f:
        f.write(TEST_LUA)
        test_lua = f.name
    try:
        print("test-run: starting nvim --headless", flush=True)
        result = subprocess.run(
            [
                "nvim",
                "--headless",
                "-c",
                f"luafile {test_lua}",
            ],
            check=False,
            text=True)
    finally:
        os.unlink(test_lua)
    if result.returncode != 0:
        return result.returncode
    print("LuaRocks/Neorg integration: PASS")
    return 0

# fmt: off
EXAMPLE = "lazy-patch.py --restore --wiperocks --apply --test-config --test-run"

def main():
    parser = argparse.ArgumentParser(
        description="Safely maintain local patches to Lazy.nvim.",
        epilog=f"Full test:  {EXAMPLE}\n\nWARNING: Might break your Neovim. BACKUP your Neovim setup before you run!\n.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="show patch state without changing files")
    group.add_argument("--status", action="store_true", help="show installed rocks and generated config status")
    group.add_argument("--diff", action="store_true", help="show differences between saved upstream and current files")
    group.add_argument("--adopt", action="store_true", help="explicitly accept current Lazy files as new upstream")
    group.add_argument("--restore", action="store_true", help="restore saved upstream files")
    parser.add_argument("--wiperocks", action="store_true", help="remove LuaRocks installation trees")
    parser.add_argument("--apply", action="store_true", help="apply the managed Lazy patches")
    parser.add_argument("--test-config", action="store_true", help="generate and verify Neorg configuration")
    parser.add_argument("--test-run", action="store_true", help="run the full LuaRocks/Neorg integration test")
    parser.add_argument("--system", action="store_true", help="operate on system/root rock trees; requires root")
    args = parser.parse_args()
    def usage_error(message):
        parser.error(f"{message}\n\nExample: {EXAMPLE}")
    if args.system and not args.wiperocks:
        usage_error("--system only applies to --wiperocks")
    if len(sys.argv) == 1: parser.print_help()
    try:
        if args.restore and restore(): return 1
        if args.wiperocks: wipe_rocks(system=args.system)
        if args.adopt and adopt(): return 1
        if args.apply and apply(): return 1
        if args.check and check(): return 1
        if args.status: status()
        if args.diff: diff()
        if args.test_config: test_config()
        if args.test_run and test_run(): return 1
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
