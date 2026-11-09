# 4d-plugin-jsmin
4D port of [JSMin](https://github.com/douglascrockford/JSMin) by Douglas Crockford 

## Manual versioning and publication

The verified default branch is `master`, but both workflows operate on the ref
explicitly selected in Actions; neither assumes that only the default branch can
be released. **Bump version** accepts `patch`, `minor` or `major`. It checks out
the immutable selected `github.sha`, requires a clean checkout and validates
source metadata before committing only `JSMin.xcodeproj/project.pbxproj`,
`Info.plist` and `English.lproj/InfoPlist.strings` to the selected branch.

The selected remote branch must still equal the dispatched SHA before and after
preparing the commit. The required executable `.github/scripts/bump-hooks/pre-push`
also compares receive-pack's advertised old SHA with that exact selected SHA,
rejecting late advancement, ancestor rewind, deletion and same-result races
after the final `ls-remote`. A missing/nonexecutable guard fails closed. Push is
nonforce, targets only the explicit branch and disables tag following with both
`push.followTags=false` and `--no-follow-tags`. Bump creates no tag and does not
start Build. If it rejects branch movement, select the branch again and dispatch
a new bump; do not reuse the stale selection.

**Build** is a separate `workflow_dispatch`-only workflow with **zero inputs**
beyond Actions' ref selector. Every checkout uses `github.sha`. It validates
strict source `X.Y.Z` and derives `vX.Y.Z`, `JSMin-X.Y.Z.zip` and
`JSMin-X.Y.Z.dmg`; there is no typed tag or tag-push trigger. Windows x64
MSBuild/v143, its exact output path and PE x64 check, macOS universal
arm64/x86_64 validation, Windows artifact merge, Developer ID signing/strict
verification, both ZIP/DMG notarizations and DMG stapling remain required gates.
Existing SDK/API/framework dependencies, secret names and packaging stay intact.

Build uses one constant repository-wide publication concurrency group across
branches. Before native work, and again immediately after all gates and before
publication, it checks remote tags and authenticated, explicitly paginated
release lists **including drafts**. Every page and entry is schema-validated.
API 404, authentication, network, malformed-response and later-page failures
stop publication; only a complete successful no-match permits creation.
Source version files must still match the selected commit at both checks.

Publication is create-only: POST `git/refs` creates the tag at the exact selected
SHA (even a concurrent same-SHA creation is an error), followed by remote SHA
verification. A separate POST `releases` explicitly sets `tag_name`,
`target_commitish`, `name`, `draft=false`, `prerelease=false` and the original
empty notes policy (no generated notes). Separate asset POSTs upload only to the
returned new release ID. There is no update, overwrite, clobber, deletion,
rollback or retry, and no create-with-assets temporary draft.

**Partial-state recovery:** failures retain any accepted tag, public release and
uploaded assets, including ambiguous network responses. Inspect the Actions
error, remote tag SHA, draft/public release list and assets before deciding what
to do. A rerun intentionally refuses an existing version rather than repairing
it. An authorized maintainer must explicitly decide how to recover retained
state outside this workflow, or use a new source version after inspection.
Never assume a failed upload removed the tag or release.

### Source metadata contract and migration evidence

The old bump header (introduced in `f87453e`) explicitly chose
`MARKETING_VERSION` when present, falling back to `CURRENT_PROJECT_VERSION` only
for older-style projects predating that split; it did **not** promise to bump
both. `d9faf6a` introduced six marketing/current-project settings at 2.0.0.
Subsequent bumps through `b8a2984` changed only marketing to **2.0.3**.
All six `CURRENT_PROJECT_VERSION=2.0.0` settings are therefore retained build
metadata, not normalized to marketing or claimed to be an independently
incrementing mechanism.

The target's three `INFOPLIST_FILE = Info.plist` settings use the root plist.
Its short version was still 2.0.0. The source English `InfoPlist.strings` is
explicitly copied by the Resources build phase and its 1.0 short/info strings
override displayed bundle metadata. Those display surfaces are repaired to the
existing marketing authority **2.0.3**, without a release increment. The source
UTF-8 BOM is retained and legacy CR-only localized lines are normalized to LF.
`CFBundleVersion` remains absent. Supported Xcode references are resolved and
preserved; an optional valid bundle build version is validated separately and
never rewritten. Current-project build settings, localization revision counters,
prebuilt bundles, native dependencies, manifest/4D/schema metadata are untouched.

Helpers and regressions adapt reviewed prior art from
[miyako/4d-plugin-structure-access#1](https://github.com/miyako/4d-plugin-structure-access/pull/1)
(`af1b65e6da2c61636a946a4b6ca2b4d9245da569`),
[miyako/4d-plugin-kotoeri-option#1](https://github.com/miyako/4d-plugin-kotoeri-option/pull/1)
(`4b6eca34d855aa1d8f66c8ef6e62b96e8748ebd0`) and
[miyako/4d-plugin-script#1](https://github.com/miyako/4d-plugin-script/pull/1)
(`4cdf7b5d4ec645385654e6cb17a2ff0603925fb5`), retaining JSMin's actual
marketing-first contract, paths, native jobs and asset shapes.

Focused local checks (no native/signing execution):

```sh
python3 -m unittest discover -s .github/tests -v
actionlint .github/workflows/*.yml
sh -n .github/scripts/bump-hooks/pre-push
```

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
