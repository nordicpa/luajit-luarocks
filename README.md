# Resurrecting LuaJIT for Neovim

After about 18 months of frustration and confusion caused by a LuaJIT bug blocking Neovim, we hobbyist Neovim users finally took matters into our own hands.

* **luarocks/luarocks #1797:** The primary upstream GitHub bug tracker.
* **Kong Gateway:** Tracked under internal Knowledge Base Article 000002860 and developer tracking issue `Kong/kong #14598`.
* **Apache APISIX:** Tracked under GitHub issue `apache/apisix #12274`.

We knew what we wanted, and ChatGPT was there to help.

Our goal was to fully resurrect LuaJIT as a first-class citizen on any Linux, Unix-like, or macOS system, configured however one wishes: in a local user-home folder, globally across the entire system for all users, **or both at the same time**. Additionally, it needed full privileges and the ability to coexist seamlessly and in parallel with any and all other Lua versions. We believe this `luarocks-jit` setup can handle any Lua version in parallel simply by providing detailed `/etc/luarocks/config-5.([1-4]|jit).lua` configurations and running on any Lua version, including LuaJIT (5.1).

We spent a tremendous amount of time on this and likely overengineered it—at least according to Grok, though Gemini insists we did a fantastic job. We have no idea who is right, but we built it exactly how we wanted it, and so far, it works precisely as intended.

So far, we have only tested it with a local user installation for `nvim-treesitter`, but we will likely test a system-wide installation soon. Our primary test case is compiling both **C and C++ binaries** for `nvim-neorg/tree-sitter-norg` Norg Treesitter Parser that was previously impossible for Neovim.

We are attaching the working test script below.

Full test:  lazy-patch.py --restore --wiperocks --apply --test-config --test-run

WARNING: Might break your Neovim. BACKUP your Neovim setup before you run!
