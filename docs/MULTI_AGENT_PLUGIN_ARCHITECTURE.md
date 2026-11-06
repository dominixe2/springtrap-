# Multi-agent and plugin execution architecture

## Product behavior

Micro Helper remains one assistant with one identity, one memory, one conversation
history, and one task state. A planner may split a request into any number of
independent subtasks. The coordinator dispatches those subtasks to the most
suitable available model/tool adapters, runs independent work concurrently,
collects failures as well as successes, and asks a synthesizer to produce one
coherent Czech answer or deliverable.

The number of agents is selected per task. A concurrency limit is a resource
control, not a fixed agent-count limit. The coordinator must not launch duplicate
agents merely to inflate the count.

## Provider and tool families to support

- Model providers: Ollama/local models, OpenAI (including Codex-capable
  workflows where the user's account and supported integration permit them),
  Anthropic Claude, Google Gemini, Groq, Mistral, DeepSeek, and compatible
  OpenAI-style endpoints.
- Research and web engines: approved search providers, browser retrieval, and
  source-grounded synthesis.
- Creation engines: image generation, audio/speech, video where an authorized
  provider exists, code/build systems, and game/animation engines.
- Creative software and engines: Blender, Godot, Unity, Unreal Engine, and
  specialist animation/Anime production services when their official APIs or
  safe browser workflows are available.
- Productivity and device tools: files, Git hosting, calendar, email, Android
  companion, and paired Windows worker, each through explicit adapters.

This is a compatibility target, not a claim that every named service currently
has a free API or can be controlled from a phone. Each adapter must declare
capabilities, availability, data handling, cost class, required permissions,
and whether it can perform external side effects.

## Cost and permission policy

1. Free/local adapters are preferred.
2. Paid providers remain disabled unless the user explicitly enables paid use.
3. Never infer that a consumer subscription includes API credits.
4. Show quota/rate-limit failures and fall back to another eligible adapter.
5. Private data is not sent to cloud providers without the applicable consent.
6. Model output is never authorization. Publishing, purchases, messages,
   account changes, code deployment, deletion, and other consequential actions
   require operation-specific approval.
7. Plugin installation is voice-triggerable, but discovery and installation
   must be restricted to trusted catalog entries, show requested permissions,
   verify publisher/source and package integrity, and ask before granting access.
   Arbitrary websites must not be allowed to inject executable plugins.

## Voice plugin workflow

A spoken command such as "Přidej plugin pro Blender" starts a discovery flow:
search the trusted catalog, explain what the plugin can do and what permissions
it needs, show whether it is free or paid, then request confirmation before
installation and permission grants. "Přidej anime engine" should search for
supported animation/video creation integrations and report the actual
capabilities and costs rather than promising that an entire website can be
embedded as an engine.

## Current implementation boundary

The first code primitive is `src/micro_helper/orchestration.py`: it accepts a
planner-produced list of subtasks, distributes them across available provider
adapters, runs them concurrently with a configurable concurrency limit, retains
per-agent failures, and calls a synthesizer exactly once. It is not yet wired
into the API, task worker, provider credentials, voice UI, plugin catalog, or
Android/Windows pairing. Those integrations require separate implementation
and end-to-end tests.
