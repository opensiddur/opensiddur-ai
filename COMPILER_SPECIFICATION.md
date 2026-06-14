# JLPTEI Compiler Specification

## Overview

The JLPTEI compiler transforms valid JLPTEI XML files with transclusions and annotations into a single, linear intermediate XML file suitable for export. The compiler handles:

1. Internal and external transclusions
2. ID remapping for uniqueness after transclusion
3. Conditional text (`j:conditional`): resolved true/false inclusion, or undefined/maybe with retained markers and instructions
4. Out-of-line annotations (commentaries and editorial notes)
5. Instructional note replacement based on priority
6. Header information inclusion

## Architecture

### Processor Types

The compiler has three processor classes, each handling different transclusion scenarios:

1. **CompilerProcessor**: Base processor for full document compilation
2. **ExternalCompilerProcessor**: Handles external transclusions (preserves element structure)
3. **InlineCompilerProcessor**: Handles inline transclusions (extracts text content)

### Key Components

- **LinearData**: Singleton holding shared state (processing context stack, conditional settings stack, conditional scope stack, project priorities, XML cache)
- **ReferenceDatabase**: SQLite database mapping URNs to file locations and element paths
- **UrnResolver**: Resolves URN references to actual file locations using the reference database

## Processing Context State Machine

### Context Structure

The `processing_context` is a stack (list) of `_ProcessingContext` dictionaries, with each entry representing one level of processing scope:

```python
_ProcessingContext = {
    project: str,                    # Current project name
    file_name: str,                  # Current file name
    element_path: Optional[str],      # XPath to current element (set during processing)
    from_start: Optional[str],       # Start URN for range processing
    to_end: Optional[str],           # End URN for range processing
    before_start: bool,              # True if before start element in range
    after_end: bool,                 # True if after end element in range
    include_tail_after_end: bool,    # Include tail text after end element
    exclusive_end: bool,              # End is exclusive (before milestone)
    inside_deepest_common_ancestor: bool,  # Inside DCA for external transclusions
    command: _ProcessingCommand      # Current processing command
}
```

### Processing Commands

The `command` field determines how an element is processed:

- **COPY_AND_RECURSE**: Copy element with text content, process children
- **COPY_ELEMENT_AND_RECURSE**: Copy element without text content, process children
- **RECURSE**: Process children without copying element
- **SKIP**: Skip element and all children
- **COPY_TEXT_AND_RECURSE**: Extract text content, process children (inline mode)

### Context Lifecycle

1. **Push**: When `process()` is called, a new context is pushed onto the stack
2. **Update Before**: `_update_processing_context_before()` sets `element_path` and determines `command`
3. **Update After**: `_update_processing_context_after()` clears `element_path` and updates state flags
4. **Pop**: When `process()` completes, the context is popped from the stack

### State Transitions

#### CompilerProcessor (Base)

- Initial state: `before_start=False`, `after_end=False`, `command=COPY_AND_RECURSE`
- Context updated before/after each element to track `element_path`
- No range-based state transitions

#### ExternalCompilerProcessor

State machine tracks position relative to transclusion range:

1. **Before Start**: `before_start=True`, `command=RECURSE` (skip content)
   - When reaching deepest common ancestor: `inside_deepest_common_ancestor=True`, `command=COPY_ELEMENT_AND_RECURSE`
   - When reaching start element: `before_start=False`, `command=COPY_AND_RECURSE`

2. **Between Start and End**: `before_start=False`, `after_end=False`, `command=COPY_AND_RECURSE`
   - Normal processing of transcluded content

3. **After End**: `after_end=True`, `command=SKIP`
   - All subsequent elements skipped
   - `include_tail_after_end` flag controls tail text inclusion

#### InlineCompilerProcessor

Simpler state machine for text extraction:

1. **Before Start**: `before_start=True`, `command=RECURSE` (skip content)
2. **Between Start and End**: `before_start=False`, `after_end=False`, `command=COPY_TEXT_AND_RECURSE`
3. **After End**: `after_end=True`, `command=SKIP`

## Hierarchical Processing Algorithm

### Main Process Flow

The `process()` method orchestrates the compilation:

1. **Initialize**: Set root language, push processing context
2. **Process Root**: Call `_process_element()` on root element
3. **Mark Source**: Add `p:file_name` and `p:project` attributes if needed
4. **Cleanup**: Pop processing context

### Element Processing (`_process_element`)

For each element, the processor:

1. **Update Context Before**: Determine processing command based on current state
2. **Conditional content skip**: If any open `j:conditional` scope evaluated false, skip liturgical/content elements until the matching `j:endConditional` (control elements are exempt; see [Conditional text](#conditional-text))
3. **Settings / condition markers**: Handle `j:declare`, `j:endDeclare`, `j:conditional`, `j:endConditional`
4. **Check Transclusion**: If element is `j:transclude`, process transclusion
5. **Check Annotations**: Gather annotations for this element
6. **Handle Replacement**: If annotation command is REPLACE, return replacement element
7. **Copy Element**: Create new element with same tag and attributes
8. **Process Children**: Recursively process all children
9. **Handle Insertions**: Insert annotations if command is INSERT
10. **Rewrite IDs**: Update `xml:id`, `target`, and `targetEnd` attributes with path hash
11. **Update Context After**: Update state flags (especially `after_end`)
12. **Return**: Return processed element(s)

### ID Rewriting

To ensure uniqueness after transclusion, IDs are rewritten using a hash of the processing path:

- Path includes: `project/file_name:element_path` for each context level
- Hash: SHA256 of full path, truncated to 8 characters
- Rewritten IDs: `{original_id}_{hash}`
- Target references: `#ref` becomes `#ref_{hash}`

## Conditional settings and conditional text

### Settings stack (`j:declare`)

Feature-structure settings are pushed onto `linear_data.conditional_settings` by YAML `declarations` at compile init and by `j:declare` / `j:endDeclare` in source XML. The active value for a feature is the latest matching entry on the stack. `j:declare` markers are always stripped from output.

Each `process()` call runs inside a checkpoint that truncates both `conditional_settings` and `conditional_scope_stack` on exit, so transcluded file compilations cannot leak scopes into the parent.

### Conditional text (`j:conditional`)

Scoped liturgical content lies between a `j:conditional` element and its matching `j:endConditional` (siblings in document order, same pattern as `j:declare`). When the opening marker is encountered:

1. The condition (feature structures and `j:all` / `j:any` / `j:none` / `j:one` combinators) is evaluated against active settings.
2. A `ConditionalScope` entry is pushed onto `linear_data.conditional_scope_stack`.
3. Sibling content until `j:endConditional` is included or skipped based on the result.

| Evaluation | Scoped content | Instruction note in `j:conditional` | Markers in output |
| --- | --- | --- | --- |
| **true** | Include | Exclude | Strip |
| **false** | Exclude | Exclude | Strip |
| **undefined** | Include | Include | Retain |

**Undefined features:** if a condition references a feature with no active setting, the active value is treated as undefined (`tei:default` / YAML `null` semantics). Comparing a concrete condition to an undefined active value yields **undefined**.

**Nested conditionals:** content is skipped if *any* open scope on the stack is false.

**Control elements exempt from conditional skip** (always processed, always stripped except when undefined markers are retained):

- `j:declare` / `j:endDeclare` — settings stack is updated even inside a false conditional; liturgical content between them is still excluded.
- `j:conditional` / `j:endConditional` — scopes are pushed/popped to keep the stack consistent across nesting.

Evaluation uses tristate logic with truth tables from JLPTEI-3 (`condition_eval.py`). Undefined evaluation is compile-time “include all possibilities”: one linear output that includes the text, the reader instruction, and the conditional markers for downstream resolution.

### Derived settings (feature defaulting)

Many JLPTEI feature structures are **derived** from other settings (e.g. `opensiddur:hebrew-date` from `opensiddur:gregorian-date` and `opensiddur:location`; `opensiddur:holiday` from dates, times, and location). See `schema/JLPTEI-3.md` for the full derivation graph.

Derived entries use `source="derived"` on the settings stack, with a `contributors` set recording the `declare_id` of each input feature’s winning entry. Derived entry IDs are deterministic: `__derived__:{fs_type}:{feature_name}`.

**Explicit beats derived:** if the winning stack entry for a feature is `init` or `declared`, derivation for that feature is skipped (last explicit setting prevails).

**Recalculation triggers:** `recalculate_derived_settings()` runs on YAML init (`SettingChangeTrigger.INIT`), each `j:declare` (`DECLARE`), and each `j:endDeclare` (`END_DECLARE`).

**Scope rollback:** when a contributor declare scope ends, derived entries listing that `declare_id` in `contributors` are removed, then derivations are recomputed from the remaining stack (restored init or outer declares may supply inputs again).

**Override defaults:** `opensiddur:override` features are never auto-calculated; on init they default to `false` unless explicitly declared.

Note: `tei:default` in **conditions** means undefined/any-value for tristate evaluation — not derived feature defaulting.

#### Three defaulting strategies (design comparison)

| | **(1) Lazy at conditional** | **(2) Eager on declare** | **(3) Eager at init + update** |
|---|---|---|---|
| When derived values appear | First lookup during condition evaluation | Each INIT / DECLARE; removed/rebuilt on END_DECLARE | Same as (2), plus static defaults at INIT |
| Spec alignment | Weak — JLPTEI-3 recalc at setting change point | **Strong** — matches spec and existing hooks | Strong; (3) is (2) + init-time static defaults |
| Stack / contributor model | Ad-hoc cache + invalidation | **Reuses** `contributors` + `derived_dependency_index` | Same as (2) |
| Correctness across document order | OK if cache invalidated on every declare | **Deterministic** before every element | Same as (2) |

**Chosen approach:** (2) eager on declare/init/endDeclare, with the static-default slice of (3) for `opensiddur:override` at INIT. Implementation: `derived_settings.py`, `derivation_graph.py`, `calendar/`.

## Transclusion Processing

### Transclusion Types

1. **External** (`type="external"`): Preserves element structure
   - Creates `p:transclude` wrapper element
   - Uses `ExternalCompilerProcessor` to extract range
   - Children are appended to wrapper

2. **Inline** (`type="inline"` or default): Extracts text content
   - Creates `p:transcludeInline` wrapper element
   - Uses `InlineCompilerProcessor` to extract text
   - Text content concatenated into wrapper

### Range Resolution

Transclusions reference ranges via URNs:

1. **Resolve URNs**: Use `UrnResolver.resolve_range()` to find start/end elements
2. **Prioritize**: Select highest priority project from `project_priority`
3. **Find Elements**: Locate elements via XPath using `@corresp` or `@xml:id`
4. **Handle Milestones**: If end is milestone, find actual end element
5. **Deepest Common Ancestor**: For external transclusions, find DCA of start/end

### Deepest Common Ancestor (DCA)

For external transclusions, the DCA is the lowest element containing both start and end:

- If start and end are siblings, return start element
- Otherwise, walk up ancestor chain from start until end is found in descendants
- DCA determines what structure to preserve around the transcluded range

## Annotation Processing

### Annotation Types

1. **Instructional Notes** (`tei:note[@type="instruction"]`):
   - Look up alternative instructions by URN
   - Prioritize by `instruction_priority`
   - If higher priority found: REPLACE current instruction
   - Otherwise: KEEP current instruction

2. **Commentary/Editorial Notes** (standoff annotations):
   - Look up references by `@corresp` or `@xml:id`
   - Filter by `annotation_projects`
   - Prioritize by project priority
   - INSERT as first children of annotated element

### Annotation Commands

- **INSERT**: Insert annotations as first children of element
- **REPLACE**: Replace element with annotation
- **KEEP**: Keep element as-is (for instructions without alternatives)
- **NONE**: No annotation action needed

### Language Handling

Annotations may have different languages than their context:

- Compare `xml:lang` of annotation vs. insertion context
- If different, add `xml:lang` attribute to annotation element
- Language determined by first processed element's `xml:lang` or ancestor's `xml:lang`

## File Source Marking

Elements are marked with their source file when processing context changes:

- Attributes: `p:file_name` and `p:project` (in processing namespace)
- Only added when: previous context differs from current, or this is first context
- Applied to: transcluded elements, annotations, and root elements

## Special Cases

### Exclusive End

When end URN is a milestone, the actual end is exclusive:

- Find next milestone at same or higher level
- If found: end before that milestone
- If not found: include all siblings up to last sibling

### Tail Text Handling

Tail text (text after element's closing tag) is preserved:

- For `COPY_AND_RECURSE`: Tail attached to last processed child
- For inline mode: Tail concatenated to text content
- `include_tail_after_end` flag controls inclusion after end element

### Nested Transclusions

Transclusions can contain other transclusions:

- Each creates its own processing context
- IDs rewritten with nested path hashes
- File source marking reflects deepest level

## Output Format

The compiled output:

- Is valid XML (not necessarily valid TEI)
- Uses processing namespace (`p:`) for metadata
- Contains all transcluded content inline
- Has unique IDs via rewriting
- Includes annotations as first children
- Preserves language attributes where needed
- Marks file sources for traceability

## Detailed State Machine Diagrams

### ExternalCompilerProcessor State Flow

```
[Initial State]
    |
    v
[before_start=True, after_end=False]
    |
    | (traverse tree)
    |
    v
[Reach DCA?]
    | Yes
    v
[inside_deepest_common_ancestor=True, command=COPY_ELEMENT_AND_RECURSE]
    |
    | (continue traversal)
    |
    v
[Reach start element?]
    | Yes
    v
[before_start=False, command=COPY_AND_RECURSE]
    |
    | (process transcluded content)
    |
    v
[Reach end element?]
    | Yes
    v
[after_end=True, command=SKIP]
    |
    | (skip remaining elements)
    |
    v
[End]
```

### InlineCompilerProcessor State Flow

```
[Initial State]
    |
    v
[before_start=True, after_end=False, command=RECURSE]
    |
    | (traverse tree, skip content)
    |
    v
[Reach start element?]
    | Yes
    v
[before_start=False, command=COPY_TEXT_AND_RECURSE]
    |
    | (extract text content)
    |
    v
[Reach end element?]
    | Yes
    v
[after_end=True, command=SKIP]
    |
    | (skip remaining elements)
    |
    v
[End]
```

## Processing Context Stack Behavior

The processing context stack grows as nested transclusions are encountered:

```
Stack Level 0: Root document processing
    |
    | (encounters j:transclude)
    |
    v
Stack Level 1: External transclusion processing
    |
    | (encounters another j:transclude)
    |
    v
Stack Level 2: Nested transclusion processing
    |
    | (completes)
    |
    v
Stack Level 1: Resume external transclusion
    |
    | (completes)
    |
    v
Stack Level 0: Resume root document
```

Each level maintains its own:
- Project and file name
- Range boundaries (from_start, to_end)
- State flags (before_start, after_end, etc.)
- Processing command

## ID Rewriting Algorithm

The ID rewriting process ensures global uniqueness:

1. **Build Path String**: For each context in the stack:
   - Format: `project/file_name:element_path`
   - Join contexts with `+`
   - Append current element path if available

2. **Generate Hash**: 
   - SHA256 hash of path string
   - Truncate to first 8 characters

3. **Rewrite Attributes**:
   - `xml:id`: `{original_id}_{hash}`
   - `target`: Rewrite each `#ref` to `#ref_{hash}`
   - `targetEnd`: Same as target

Example:
- Original: `xml:id="verse1"`, path hash: `a3f2b1c9`
- Rewritten: `xml:id="verse1_a3f2b1c9"`

## URN Resolution Process

1. **Parse URN**: Extract URN from `@target` or `@corresp`
   - May include range notation: `urn:.../1/1-2`
   - May include project specifier: `urn@project`

2. **Resolve Range**: Use `UrnResolver.resolve_range()`
   - Split range notation into start/end URNs
   - Query reference database for matches

3. **Prioritize**: Apply `project_priority` list
   - Select highest priority project
   - Ensure start and end are in same file

4. **Locate Elements**: Use XPath to find elements
   - For URNs: `./descendant::*[@corresp='{urn}']`
   - For IDs: `./descendant::*[@xml:id='{id}']`

5. **Handle Milestones**: If end is milestone element
   - Find next milestone at same/higher level
   - Adjust end element accordingly

## Annotation Resolution Process

### For Instructional Notes

1. Extract `@corresp` URN from note element
2. Query `UrnResolver.resolve()` for all matching notes
3. Apply `instruction_priority` to select best match
4. If found and different project: REPLACE current note
5. Otherwise: KEEP current note

### For Commentary/Editorial Notes

1. Extract `@corresp` URN or `@xml:id` from element
2. Query `ReferenceDatabase.get_references_to()` for matching notes
3. Filter by `annotation_projects` list
4. Apply project priority (if `return_all=False`, get highest priority)
5. Process each matching reference:
   - Create new `CompilerProcessor` for reference's project/file
   - Process the referenced note element
   - Mark file source if from different project
   - Add language attribute if different from context
6. INSERT all annotations as first children

## Implementation Details

### Namespace Handling

- JLPTEI namespace: `http://jewishliturgy.org/ns/jlptei/2` (prefix: `j`)
- Processing namespace: `http://jewishliturgy.org/ns/processing` (prefix: `p`)
- TEI namespace: `http://www.tei-c.org/ns/1.0` (prefix: `tei`)

### Element Creation

All new elements created during processing:
- Preserve original namespace mappings
- Add processing namespace to map
- Copy relevant attributes from source
- Maintain text and tail content appropriately

### Error Handling

The compiler raises `ValueError` for:
- URN not found in reference database
- Start/end elements not found in source file
- Start and end in different files (for ranges)
- No prioritized URN found (after filtering)

### Performance Considerations

- XML cache: Parsed XML files are cached to avoid re-parsing
- Reference database: Pre-indexed URN mappings for fast lookups
- Context stack: Minimal overhead for shallow nesting
- ID rewriting: Hash computation is fast (SHA256 truncated)

## Examples

### Example 1: Simple External Transclusion

**Input:**
```xml
<j:transclude type="external" target="urn:x-opensiddur:test:doc/1/1" 
              targetEnd="urn:x-opensiddur:test:doc/1/3"/>
```

**Processing:**
1. Resolve URNs to elements in source file
2. Find deepest common ancestor
3. Use ExternalCompilerProcessor to extract range
4. Create `p:transclude` wrapper
5. Append processed children

### Example 2: Inline Transclusion with Annotation

**Input:**
```xml
<p xml:id="verse1">
  <j:transclude type="inline" target="urn:x-opensiddur:test:doc/1/1"/>
</p>
```

**Processing:**
1. Resolve URN to start element
2. Use InlineCompilerProcessor to extract text
3. Create `p:transcludeInline` with text content
4. Look up annotations for `xml:id="verse1"`
5. Insert annotations as first children of `p`

### Example 3: Instructional Note Replacement

**Input:**
```xml
<note type="instruction" corresp="urn:x-opensiddur:test:instruction/1"/>
```

**Processing:**
1. Query for alternative instructions with same URN
2. Find higher priority instruction in different project
3. Process replacement instruction element
4. REPLACE current note with replacement

## Testing Considerations

The compiler should be tested for:
- Simple transclusions (external and inline)
- Nested transclusions
- Range transclusions with milestones
- Exclusive end handling
- ID rewriting uniqueness
- Annotation insertion and replacement
- Language attribute propagation
- File source marking
- Edge cases (empty ranges, missing URNs, etc.)

