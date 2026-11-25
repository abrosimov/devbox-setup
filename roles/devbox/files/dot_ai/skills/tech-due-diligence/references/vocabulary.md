# Vocabulary of findings and ratings

The terms that carry the analysis. Use them with these meanings only, and define them in the
document's "how to read the findings" section.

## Levels of evidence: named, shown, working

| Level | Meaning | Reached by |
|---|---|---|
| **Named** | the material names the tool, component or practice | a deck, a brochure, a sales answer |
| **Shown** | its configuration or set-up has been seen | a screenshot of configuration, a configuration file, an account view |
| **Working** | its records show it doing its job | logs, alert history, restore-test records, billing records |

A sell-side deck reaches "named" only. A screenshot in a deck shows what was on a screen when the
slide was made, not what is set up now; say which.

## Kinds of finding

- **Confirmed problem**: the material or a public source establishes a problem, at the strength
  the source allows (for example, the maker's promise of security fixes for a named component has
  ended).
- **Confirmed fact with open risk**: something is established and carries a risk whose size is
  not known (a named dependency whose monitoring is not named).
- **Blank spot**: the material does not say, and public sources cannot tell.

## Ratings

| Rating | Definition |
|---|---|
| **Red** | a confirmed problem with a business consequence |
| **Amber** | a confirmed fact with open risk; or a blank spot that a confirmed fact makes more likely to matter |
| **No data** | a blank spot that nothing known makes more likely to matter than on any comparable platform |

- **Amber versus No data for a blank spot.** The blank spot is Amber when a confirmed fact raises
  its stakes: the deck names the dependency, states a volume, or a public source shows a weakness.
  Otherwise it is No data. Write this distinction into the document's own definitions.
- **Nothing is Green** without evidence at the "working" level, which an initial DD does not have.
- **Every rating passes the document's own definition.** In stage 5, read each rating against
  the definition as written; a rating that fits only a looser reading is changed.

## Fields of a finding

**What we see**: the observation, with its source. **Why it matters**: the business
consequence, in plain words. **Not known**: what the material and public sources could not
settle. **First step**: one concrete check, request or question.

## Naming

- One object, one name: choose a name at first mention and keep it in every part.
- A rename is a change: propagate it to the summary, body, appendices and glossary.
- A word the owner had to ask about goes into the glossary or is replaced by what it means.
