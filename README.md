# 4d-plugin-jsmin
4D port of [JSMin](https://github.com/douglascrockford/JSMin) by Douglas Crockford 

`JSMin` is a single-command 4D plugin that minifies JavaScript source text: it strips comments and collapses insignificant whitespace while preserving the token boundaries needed to keep the code semantically identical. It's a pure text-in/text-out plugin — it doesn't parse or execute JavaScript, doesn't touch the file system, and doesn't call any OS-level API, so there are no platform-specific behaviors to account for.

| Command | Returns | Purpose |
|---|---|---|
| [`JSMin`](#jsmin) | Text | Minifies a JavaScript source string (removes comments, collapses whitespace) |

**Platforms:** macOS, Windows — the implementation is a single shared code path with no `#if` platform branches, so behavior is identical on both.

---

## Requirements & platform notes

- No permissions, OS APIs, or external dependencies are involved — the command runs entirely in-process on the Text value you pass it.
- The command takes exactly one mandatory parameter and always returns a Text result. There's no optional-parameter form and no overload.
- **Malformed input can hang the call rather than error out.** If the source text contains a string literal, `/* */` comment, or regular-expression literal that isn't properly closed, source-level review of the current build shows the command can fail to return a result at all, leaving your calling method waiting indefinitely. This hasn't been confirmed by running the compiled plugin in this environment, but the code path is reachable from an ordinary call with no special input needed beyond a truncated/malformed string — see [Error handling & troubleshooting](#error-handling--troubleshooting) below before feeding it untrusted or partial source.

---

## JSMin

**`JSMin ( source ) → Text`**

### Syntax

```4d
JSMin ( source ) : Text
```

| Parameter | Type | Description |
|---|---|---|
| `source` | Text | JavaScript source code to minify. |
| Result | Text | The minified JavaScript: comments removed, whitespace collapsed wherever it's safe to do so. |

### Description

`JSMin` implements a C++ port of Douglas Crockford's `jsmin` algorithm: a single-pass tokenizer that strips both `//` line comments and `/* */` block comments, and reduces runs of whitespace to the minimum needed to keep adjacent tokens from merging into something different (e.g. it won't let `a + +b` collapse into `a ++b`). It performs no JavaScript parsing/validation beyond what's needed to tokenize correctly — it will not tell you the input is syntactically invalid JavaScript, and passing a well-formed empty string returns an empty string safely.

The whole `source` argument is processed in one call; there's no streaming or chunked form. Because 4D Text values are passed and returned directly, there's no manual encoding conversion to do on your end — read the source file as Text (as the sample below does via `Document to text`) and pass it straight through.

**Known limitation:** an unterminated string, block comment, or regular-expression literal inside `source` can leave the plugin unable to return control to your method (see the requirements note above). Until this is fixed upstream, validate that the JavaScript you're feeding it is syntactically complete, or generate/fetch it from a source you trust to be well-formed.

### Example

From the plugin's own test method (`test.4dm`):

```4d
//%attributes = {}
$path:=Get 4D folder:C485(Current resources folder:K5:16)+"jquery.js"
//$path:=System folder(Desktop)+"dlg0_001.js"
$src:=Document to text:C1236($path; "utf-8")
$start:=Milliseconds:C459
$dst:=JSMin($src)
$duration:=Milliseconds:C459-$start
SET TEXT TO PASTEBOARD:C523($dst)
```

This reads `jquery.js` out of the current resources folder as Text, minifies it, times the call, and copies the minified result to the pasteboard.

Minifying an in-memory string directly:

```4d
$src:="function add(a; b)\n{\n  // sum two numbers\n  return a+b\n}"
$minified:=JSMin($src)
ALERT($minified)
```

Combine the result with any of 4D's own document-writing commands to save it back out to a `.js` file — check your Language Reference for the exact command/tag on your 4D version, since that varies by release.

---

## Error handling & troubleshooting

- **A malformed literal in the source can hang the call instead of raising an error.** An unclosed string, block comment, or regex literal is not rejected with a 4D error — in the current build it can prevent the command from returning at all. Validate or sanitize source text of unknown origin before passing it to `JSMin`, and avoid calling it on partial/truncated files.
- **There's no error or status output.** `JSMin` returns only the minified Text; it does not return an object, a success flag, or any indication that something in the input looked unusual. Treat any output as "best effort" rather than a validated result.
- **Empty input is safe.** Passing an empty Text value returns an empty Text value; you don't need to guard against that case specifically.

---

## Quick reference

```4d
$src:=Document to text:C1236($path; "utf-8")
$minified:=JSMin($src)
SET TEXT TO PASTEBOARD:C523($minified)
```
