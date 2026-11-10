# Bounded native ownership audit

## Scope and immutable provenance

Audit baseline: `f429a2b58c0533a73f2c9fc727d6882d7df4d572`.
Canonical guidance: `miyako/skills` commit
`e6b492fcb81e5e1a7f7db723594b420e63bf6eb9`,
`4d-skills/skills/4dplugin/SKILL.md`.
The bundled SDK implementation has git blob
`478081f0238f6bc5393222f574bc2656f010b67b`; its header has blob
`9054b45ffc7ff6f5b8d57529a3788a55d977b314`.
These identify the actual local snapshot, not an asserted upstream SDK release.
The implementation's v14 and header's v13 comments are not upstream provenance.
The SDK implementation, ABI headers and exports remain byte- and mode-unchanged.

Regression scaffolding was adapted from `miyako/4d-plugin-get-windows-version`
commit `a7fee72f71478ce332eb2b2d827fbc28b854efbb`; its SDK and dispatcher
semantics were not assumed to match. In particular this SDK returns raw kind
zero on command-argument handle allocation failure: it does not normalize that
sentinel to a string. The five picture command calls are procedures, not
imaginary owning function returns, so the shim returns Undefined on execution.

## Complete tracked native inventory and reachability

Both `JSMin.vcxproj` and `JSMin.xcodeproj/project.pbxproj` compile the complete
`4DPlugin.cpp`, `4DPluginAPI.c` and all sixteen wrapper implementations below.
`4DPluginAPI.h` includes all wrapper headers; `C_TYPES.h` supplies string/vector
types. Xcode classifies SDK and plugin sources as Objective-C++, and its prefix
header includes Carbon. Windows compiles the SDK as C++; include paths resolve
the same `4D Plugin API` and `Classes` directories. There are no additional
tracked native source trees or separate platform SDK copies.

| Files (under `4D Plugin API/Classes` unless specified) | Ownership/reachability |
|---|---|
| Root `4DPlugin.cpp`, `4DPlugin.h` | `PluginMain` dispatches selector 1 to `JSMin`; borrowed parameter descriptor is copied into C++ UTF-16 text, then `C_TEXT::setReturn` uses a content setter. No SDK string array or picture invocation from this command. The third-party minifier namespace is unchanged. |
| `C_TEXT.cpp`, `C_TEXT.h` | Parameter strings copied into owned C++ text; parameter/return writes use `PA_SetUnistring`, not descriptor transfer. UTF-8/UTF-16 conversion and Objective-C copy helpers inspected. Copy construction/assignment already disabled. |
| `ARRAY_TEXT.cpp`, `ARRAY_TEXT.h` | Compiled but dispatcher-dormant. Borrowed array elements are copied into C++ text. Each output iteration creates a distinct SDK string; accepted insertion transfers it without a subsequent dispose. Includes index zero. Allocation-failure limits below are not certified. |
| `C_PICTURE.cpp`, `C_PICTURE.h` | Compiled but dispatcher-dormant `CPicture` implementation plus forwarding `C_PICTURE`. Confirmed defects corrected here; all five command IDs (678, 1002, 988, 457, 679), parameter/return handoffs, byte creation, metadata and Objective-C image helpers inspected. |
| `C_POINTER.cpp`, `C_POINTER.h` | Compiled but dispatcher-dormant borrowed pointer/metadata wrapper. `getVariable` uses `PA_GetPointerValue`, then copies definition fields; ownership and metadata ambiguity deferred, not blindly cleared or relabeled. |
| `C_BLOB.cpp`, `C_BLOB.h` | Compiled but dispatcher-dormant bytes/handle wrappers and hex/base64 helpers. Text via `C_TEXT` is copied; no SDK string descriptor transfer. Unrelated byte and nonstring allocation behavior unchanged. |
| `C_INTEGER.cpp/.h`, `C_LONGINT.cpp/.h`, `C_REAL.cpp/.h`, `C_DATE.cpp/.h`, `C_TIME.cpp/.h` | Five compiled scalar wrappers, value-only parameter/return reads and writes; no string owners. |
| `ARRAY_BOOLEAN.cpp/.h`, `ARRAY_INTEGER.cpp/.h`, `ARRAY_LONGINT.cpp/.h`, `ARRAY_REAL.cpp/.h`, `ARRAY_DATE.cpp/.h`, `ARRAY_TIME.cpp/.h` | Six compiled numeric/date/time array wrappers. No string owners; nonstring allocation behavior out of scope. |
| `C_TYPES.h` | Shared C++ text/vector, byte and parameter aliases; Apple framework/Windows includes. No allocation implementation. |
| `4D Plugin API/4DPluginAPI.c`, `4DPluginAPI.h`, `PrivateTypes.h`, `PublicTypes.h`, `Flags.h`, `EntryPoints.h`, `4DPluginAPI.def` | Complete unchanged SDK implementation, declarations, packed ABI, platform flags, engine selector constants and `FourDPackex` export. Ownership rules derived from actual implementations, not API names. |
| Root `4D Plugin_Prefix.pch` | Carbon include only; no ownership logic. |

Both root and prebuilt-bundle `manifest.json` declare the one scalar text
command `JSMin(&T):T`. `documentation.htm`, prebuilt HTML/resources, project
files and binary/4D database assets are not alternative native entry points.
There are no first-party JSON parse/property/element wrappers, method callbacks,
additional internal text-array callsites, or owning method-return consumers.
This conclusion follows the tracked source inventory and call traces, not just
indexed absence or the scalar manifest.

## Actual SDK contracts and surgical corrections

`PA_CreateVariable(eVK_Unistring)` allocates an empty string; the picture kind
allocates an empty picture. Both `PA_SetStringVariable` and
`PA_SetPictureVariable` overwrite descriptors without releasing old contents.
Use Undefined only for destinations immediately initialized by these setters;
retain typed initial picture outputs where the procedure fills them.

`fromFileAtPath` previously disposed `_path` explicitly and again through
`args[0]`. The argument now owns that allocation exactly once. `setPicture`
retains the output, after which the original owning output argument is cleared.
`setBytes` likewise releases its newly created picture after retaining it.
Failed picture creation preserves the original owner and observable SDK error.

`createCopy`, `createGrayScale`, `getSize`, and `createThumbnail` no longer
overwrite initial picture owners; `createCopy` also avoids overwriting an empty
string owner. Existing borrowed-picture detach operations and owning picture
handoffs remain intact. Conversion returns bytes excluding the terminator:
`createCopy` divides that count by `sizeof(PA_Unichar)` before constructing text.

`PA_GetStringInArray` borrows the element descriptor. `PA_SetStringInArray`
accepts exactly Unicode-array type, non-null data, `0 <= index <= count`, and
non-null incoming descriptor; it disposes the old element then shallow-assigns.
Rejected owners stay caller-owned. Index zero is accepted. `ARRAY_TEXT` makes
independent copies and does not dispose transferred descriptors.

Scalar `PA_SetStringVariable` shallow aliases; synchronous argument cleanup
must happen once after consumption. `PA_ReturnString` delegates to the
engine-backed `PA_SetUnistring` content setter and is not array transfer.
`PA_GetStringVariable` in this older SDK delegates to `EX_VARIABLE_TO_STRING`;
no first-party consumer exists, and a shallow-borrow implementation from a
different SDK is not substituted.

## Actual-source differential regression

```sh
python3 tests/ownership/run.py --baseline --output /absolute/scratch/ownership
```

The same final `host.mm` is linked against both full production source trees:
the working tree and immutable `git archive` baseline, including the complete
unchanged SDK and all sixteen wrappers. No replacement SDK, extracted SDK
snippets, release project phases, source minification execution in a JS engine,
or real UI/filesystem picture commands are used. Only the `gCall4D` engine
boundary is simulated. Synthetic JS strings are minified as text and compared,
never evaluated.

The runner requires every named baseline outcome, not merely any crash.
Across allocated/null empty representations there are 24 fixed passes:
18 corresponding baseline failures (`path`, `bytes`, `copy-units`,
`copy-owners`, `gray-owners`, `size-owners`, `handoffs`, `failure`,
`borrowed-param`) and six baseline passing controls (`picture-create-failure`,
`arrays`, `scalars`). Baseline failures check exact ownership assertion markers
or the `copy-units` ASan heap-buffer-overflow.

Coverage includes ASCII, BMP Omega, supplementary surrogate pairs and empty
strings; independently decoded expected text; exact UTF-8 bytes, UTF-16 units,
conversion byte capacity, string allocation length and terminator boundaries;
replacement, churn, shrink, clear, borrowed snapshots, index-zero transfers,
all setter rejection predicates, independent output allocations; synchronous
scalar aliases/content setters; picture replacement and unchanged-input cases,
borrowed detach, retained parameter/return handoff survival, failure preservation,
and raw command-allocation failure without reading/clearing its failed result.
Failed picture metadata outputs are poisoned, and production checks the error
before inspecting them.

ASan and UBSan run with abort-on-error. macOS LeakSanitizer is unavailable;
explicit string-allocation, handle-allocation and picture-reference accounting
must all return to zero in passing cases. Existing tracked bytes and executable
modes are compared against the immutable archive, with only `C_PICTURE.cpp`
and root README content exemptions.

## Explicitly deferred boundaries

- Failed initial `ARRAY_TEXT` handle creation currently publishes a text-array
  descriptor despite failure and changes the caller's original bytes. A
  separately named expected-failure probe demonstrates this on both revisions;
  it is not counted as a pass or fixed by silently dropping output. The void
  API has no established wrapper error/preservation contract; resolving that
  boundary is deferred rather than adding speculative fallback behavior.
  Engine string-creation failures in these void wrappers likewise have no
  established explicit wrapper error channel; their result descriptors and
  preservation behavior are not simulated or certified by normal string tests.
- SDK resize-allocation failure can corrupt the logical count before capacity
  is available. Normal array tests do not certify OOM safety; SDK internals are
  unchanged. Nonstring/CBytes allocation failures are outside this bounded fix.
- `PA_GetPictureData` metadata string ownership and SDK-only application-path
  strings are engine-defined/ambiguous here. The shim exercises poisoned failed
  metadata only and does not invent a successful ownership contract.
- `C_POINTER::getVariable` copies union definition metadata after
  `PA_GetPointerValue`. The SDK header's owning-return comment does not explain
  the metadata representation/lifetime. No speculative clear-then-relabel fix
  is made, and no caller reaches it from JSMin.
- Real Windows/4D, successful picture representations, actual image/file
  commands and Objective-C UI/image rendering are not executed or certified.
  macOS compilation plus a synthetic engine boundary does not reproduce or
  certify the originating Windows Poppler crash.

`Native ownership` CI is scoped to native sources/tests on `macos-latest`.
It is unsigned and has no packaging, upload, tag or publication step. Existing
manual Build/Bump workflows are unchanged and are not dispatched by this audit.
