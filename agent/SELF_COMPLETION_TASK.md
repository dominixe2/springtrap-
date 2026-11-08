undefined

## Feature requests must become implementation work
When the owner describes a new Micro Helper capability or product feature in chat, treat it as a request to change the Micro Helper product, not merely as feedback to remember or a roadmap note.

1. Translate the request into a concrete product requirement and user-visible acceptance criteria.
2. Inspect the current app and identify the actual UI, backend, persistence, permissions and tests that need to change.
3. Implement the feature in the repository on a dedicated feature branch as part of the current work cycle. Do not stop after writing a plan or adding a TODO unless a real blocker prevents implementation.
4. Add the corresponding user interface and working behavior together. For example, a request for a personal avatar means building an avatar feature in Micro Helper (avatar selection/customization, saved per-user settings and display in the app), not merely mentioning an avatar in documentation. Choose sensible defaults and ask only for decisions that materially affect the result.
5. Add automated tests and run relevant builds. Open or update a draft PR with the implementation, test evidence, preview/build artifacts and known limitations.
6. Keep working through safe, independent follow-up tasks. Pause only for a genuine blocker, a required user choice, missing access, exhausted resource budget, or an action that requires approval.
7. Never claim the feature is available in the live app until it has been merged/deployed through the authorized release process and independently verified.
8. Keep the owner informed with concise Czech progress updates and a clear distinction between implemented in a branch, tested, merged, deployed and verified live.

The default expectation is **request -> implementation -> tests -> reviewable delivery**, not **request -> promise -> backlog**. The owner may explicitly ask only to discuss or record an idea; otherwise a feature request is actionable implementation intent.
