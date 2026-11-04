# Micro Helper hosted release validation

Before the hosted source is treated as the live release:

1. Run `.github/workflows/hosted-app-checks.yml` on this branch.
2. Require the inline JavaScript syntax checks and authenticated-route checks to pass.
3. Deploy the `hosted-app/` snapshot to the existing AppDeploy app `micro-helper-ygeuyn` only after its usage limit permits deployment.
4. Require AppDeploy post-deploy QA to report zero frontend and network errors.
5. Verify sign-in, chat, persisted conversation history, user-owned memory and preferences, learning plans, task execution, web search, image generation/analysis/OCR, browser voice and two-client sync.
6. Keep the Android debug APK labeled as a test build until it points at the verified live release. It is not a Play Store release.

The GitHub source branch and the currently published AppDeploy snapshot are separate. A passing source check does not publish the hosted app.
