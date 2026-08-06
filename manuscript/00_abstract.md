# Abstract

**{{CONFIG_IDENTITY}} (codename {{CONFIG_CODENAME}})** is the Layer 3 mission
orchestrator of the BOND suite: it executes multi-package film missions
end-to-end over the `MissionProvider` protocol. A mission is a directed
acyclic graph of film packages — dependency edges exist exactly where one
film's recon outputs feed another film's recon — and the orchestrator executes
every package through the five lifecycle phases in deterministic topological
order, producing a single consolidated debrief.

The flagship canned mission, **{{CONFIG_MISSION_NAME}}**, chains
{{CONFIG_PACKAGE_CHAIN}}; its last measured execution order was
{{RESULT_EXECUTION_ORDER}}, with an all-verdicts outcome of
**{{RESULT_ALL_VERDICTS_PASS}}**.

Every outcome is recorded with provenance (an independent, deterministic
record writer — this package does not yet delegate to `bond-utilities.mission_io`,
see §7.4), and
intermediate reports persist to a state directory so an interrupted mission
resumes from its last completed step. The execution core is pure logic with
zero infrastructure imports; determinism is load-bearing: identical inputs
produce byte-identical reports, checkpoint files, and provenance records.
