# Refactor Notes

## What was refactored

[`Models/Category.cs`](../../Models/Category.cs) and
[`Models/Subcategory.cs`](../../Models/Subcategory.cs) each independently
declared the same three properties (`Id`, `Name`, `Description`) — small,
but exactly the kind of duplication [01-review-logic.md](01-review-logic.md)'s
category 4 (style/consistency) calls out, and it would only have gotten
worse as more entity types were added (this repo's own history added a
second near-identical model, `Subcategory`, right after `Category`).

## The change

Extracted the shared shape into [`Models/NamedEntity.cs`](../../Models/NamedEntity.cs):

```csharp
public abstract class NamedEntity
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
}
```

`Category` and `Subcategory` now inherit from it. `Subcategory` keeps only
what's actually specific to it — `CategoryId` and the `Category` navigation
property.

## How "nothing broke" was confirmed

[`Tests/ModelTests.cs`](../../Tests/ModelTests.cs) already characterized the
pre-refactor behavior (default `Name` is `string.Empty`, `Description`
defaults to `null`, `Subcategory.CategoryId`/`Category` round-trip) before
this change was made:

```
$ dotnet test
Passed! - Failed: 0, Passed: 4, Skipped: 0, Total: 4
```

The refactor was applied, then the same suite was re-run with no changes to
the tests themselves:

```
$ dotnet test
Passed! - Failed: 0, Passed: 4, Skipped: 0, Total: 4
```

Same 4/4 green before and after — the public shape and default values of
both models are unchanged; only where the properties are declared moved.

## Why this one, specifically

The assignment allows refactoring either the target repo or the bot itself.
This repo doesn't have deep legacy debt (it's small and recent), so the
clearest genuine duplication available was this one — real enough to be
worth fixing, small enough that the "before" and "after" behavior is fully
pinned down by four tests rather than requiring a much larger test-writing
effort just to make the refactor safe.
