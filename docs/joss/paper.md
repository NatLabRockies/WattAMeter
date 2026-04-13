---
title: "WattAMeter: A Python Toolkit for Time-Series CPU and GPU Power Monitoring in HPC"
tags:
  - Python
  - energy monitoring
  - power measurement
  - HPC
  - GPU
  - CPU
authors:
  - given-names: Weslley
    non-dropping-particle: da
    surname: Silva Pereira
    affiliation: "1"
  - name: Struan Clark
    affiliation: "1"
affiliations:
  - index: 1
    name: National Laboratory of the Rockies, United States
date: 9 April 2026
bibliography: paper.bib
---

# Summary

WattAMeter is an open-source Python toolkit for CPU and GPU power telemetry which provides synchronized time-series data during computational workloads [@wattameter_software]. It targets users who need consistent measurement workflows in scientific and engineering environments without building custom instrumentation pipelines for each project.

The software provides both a Python API and a command-line interface (CLI). At runtime, it periodically samples metrics from Linux CPU powercap/RAPL interfaces and NVIDIA GPUs through NVML, then records structured logs for downstream analysis [@linuxpowercap; @nvidia_nvml]. Optional MQTT publishing enables live integration with dashboards and external monitoring services while retaining local file output as the default persistent record [@mqtt; @wattameter_mqtt_docs].

WattAMeter is designed for high-performance computing (HPC) workflows where jobs run under schedulers, may span multiple nodes, and require measurement methods that are lightweight, portable, and non-intrusive. In addition to standalone package usage, WattAMeter is deployed as a loadable module in the National Laboratory of the Rockies' (NLR) HPC environment, where users can start and stop tracking sessions inside SLURM jobs with documented operational guidance [@nlr_wattameter_module].

# Statement of need

Energy and power are now central evaluation dimensions in computational research, especially in HPC systems where short-lived fluctuations can matter as much as totals. Users increasingly need time-resolved answers to questions such as: when power or temperature spikes occur and how to mitigate them before they stress equipment, whether short transients correlate with instability or throttling, and whether power profile history can be used to forecast near-term demand for scheduler- or runtime-level decisions. Many existing tools focus on aggregate reporting, while researchers and operators still face practical gaps when they need scheduler-aware time-series telemetry that can be embedded directly into experiments and operations workflows.

WattAMeter addresses this need by combining heterogeneous hardware telemetry into one Python-native interface and one CLI workflow. It supports periodic collection of CPU and GPU metrics in a common time-series format and can be launched as part of an experiment script or from SLURM job scripts. This lowers friction for users who need to run repeated measurements across different machines and software versions.

The package emphasizes repeatability and operational simplicity:

- deterministic sampling intervals,
- configurable write frequency while guaranteeing a final write on shutdown,
- parity between Python API and CLI interfaces,
- optional real-time publication over MQTT, and
- shell utilities that integrate with SLURM jobs.

The resulting workflow reduces the overhead for experiment instrumentation and supports comparative studies across nodes, job configurations, and application versions.

# State of the field

The ecosystem includes mature components for device telemetry and energy accounting. NVIDIA tooling and NVML bindings expose GPU counters [@nvidia_nvml], and Linux powercap/RAPL interfaces expose CPU-domain energy counters [@linuxpowercap]. At the tooling level, Scaphandre provides host-level energy metrology with exporter integrations for time-series monitoring stacks [@scaphandre], Kepler provides Kubernetes-oriented power telemetry and attribution at node/pod/container scopes [@kepler], and Zeus provides energy monitoring for deep-learning workloads with support for measurement and optimization workflows [@zeus]. CodeCarbon remains a widely used reference for process-level energy and carbon accounting [@codecarbon]. pyJoules is another well-designed Python energy-measurement library, particularly strong for process/function or code-region instrumentation workflows [@pyjoules].

Compared with this landscape, WattAMeter is explicitly Python-native for both in-code instrumentation and CLI operation, and it is designed around scheduler-managed HPC usage, including multi-node SLURM workflows. Published documentation for the tools cited above generally emphasizes exporters, dashboards, carbon accounting, or container orchestration rather than multi-node SLURM orchestration. Thus, WattAMeter is complementary to these tools: it focuses on synchronized CPU+GPU time-series telemetry in scheduler-managed HPC workflows, from which aggregate metrics such as total energy can be inferred by integration.

In terms of extensibility, Scaphandre and Kepler emphasize integration through observability/export pipelines and deployment patterns, while Zeus emphasizes programmable ML-energy measurement and optimization workflows. CodeCarbon provides strong extensibility for outputs and integrations (for example, custom output handlers and multiple built-in sinks), while hardware-tracker extension is more tightly coupled to its internal emissions and resource-tracking stack. pyJoules exposes clear device and handler abstractions, but its common usage remains centered on function- or scope-level traces. WattAMeter prioritizes backend extensibility through reader abstractions, allowing new hardware backends without changing the user-facing tracking interface in Python scripts or SLURM wrappers.

The WattAMeter contribution is a workflow-oriented collection layer that unifies CPU and GPU telemetry in one configuration model, with emphasis on scheduler-managed HPC operation. Compared with assembling custom scripts around individual low-level interfaces, WattAMeter provides:

- a unified entry point for multi-metric tracking,
- Python-native in-code instrumentation,
- direct SLURM integration through `start_wattameter` and `stop_wattameter` CLI utilities,
- multi-node session orchestration for repeated start/stop tracking within job allocations,
- file outputs for direct ingestion in analysis workflows, and
- optional MQTT streaming for live monitoring and integration with external services.

# Software design

WattAMeter follows a modular reader and tracker architecture [@wattameter_software]. Reader classes encapsulate device-specific access (for example RAPL and NVML), while tracker classes manage periodic polling, buffering, and persistence. In practice, this means users can change metrics and sampling settings without modifying the underlying collection logic.

The same architecture is intentionally designed for straightforward extension to new backends. As a concrete example, the pull request adding an `AMDSMIReader` for AMD GPU monitoring extends the existing reader model without requiring changes to the tracker abstraction [@wattameter_pr9_amdsmi].

The core tracker loop is thread-based and uses fixed sampling intervals (`dt_read`) with configurable write cadence (`freq_write`). On shutdown, trackers perform a final read/write cycle to reduce end-of-run data loss in short jobs or interrupted sessions. The implementation also supports context-manager usage and signal-aware command-line execution, which maps well to batch-system lifecycle control.

Two design choices are central for research use.

1. The software prioritizes periodic sampling over event-driven callbacks to produce uniformly sampled series that are easier to compare under controlled conditions. The tradeoff is that transients shorter than the selected interval may be missed. Each sample stores both a timestamp and a read-duration field, enabling users to assess telemetry overhead and timing fidelity in high-frequency collection.

2. WattAMeter uses dual-output semantics: local files are always first-class, and MQTT publication is optional. This ensures robust baseline operation even when network services are unavailable, while still supporting live observability when needed.

For scheduler workflows, shell utilities wrap `srun` orchestration to start and stop tracking sessions across allocated nodes, including support for multiple sequential sessions in one job allocation [@nlr_wattameter_module; @wattameter_software]. Tracking sessions do not block resources and can be started and stopped independently of the main workload. The implementation includes benchmark utilities for sampling-frequency characterization and runtime overhead estimation, plus post-processing helpers for parsing and aligning log files.

# Research impact statement

WattAMeter has practical impact for teams running experiments on mixed CPU and GPU nodes, because it packages data collection and operational orchestration into one reusable workflow. Instead of writing cluster-specific wrappers for each study, users can adopt a common interface for repeated measurement studies.

This impact is already visible in two concrete outputs. WattAMeter was used to generate the publicly released "Dataset of Generative AI Workload Power Profiles" in the NLR Data Catalog [@nlr_genai_power_dataset]. The same dataset, together with WattAMeter post-processing functionality, was then used in the study "Measurement of Generative AI Workload Power Profiles for Whole-Facility Data Center Infrastructure Planning" [@vercellino2026measurement].

Additional impact is evidenced by the deployment of WattAMeter as an NLR HPC module, with documented `module load wattameter` usage and scheduler guidance for production SLURM jobs [@nlr_wattameter_module]. The documentation includes concrete operational practices, including paired start/stop commands, interpretation of node-level CPU counters, and use of exclusive allocations for CPU analyses, indicating active use beyond a purely aspirational design.

The project is structured for ongoing reuse:

- permissive BSD-3-Clause licensing,
- command-line and API documentation with runnable examples,
- automated tests spanning readers, trackers, CLI parsing, shell utilities, MQTT, and post-processing,
- benchmark tooling for overhead characterization, and
- integration paths for both offline analysis and live monitoring.

These attributes make WattAMeter suitable as measurement infrastructure for performance studies, energy-aware benchmarking, and operations-focused workload analysis where transparent and repeatable telemetry collection is required.

# AI usage disclosure

This manuscript draft was prepared with assistance from GPT-5.3-Codex. The authors are responsible for all technical claims and manually reviewed and edited the text for accuracy and clarity.

# Acknowledgements

This work was authored by the National Laboratory of the Rockies (NLR) for the U.S. Department of Energy (DOE), operated under Contract No. DE-AC36-08GO28308. Funding was provided by the NLR. The views expressed in the article do not necessarily represent the views of the DOE or the U.S. Government. The U.S. Government retains and the publisher, by accepting the article for publication, acknowledges that the U.S. Government retains a nonexclusive, paid-up, irrevocable, worldwide license to publish or reproduce the published form of this work, or allow others to do so, for U.S. Government purposes.

We thank Matt Selensky (NLR) for maintaining the WattAMeter module on the NLR HPC system and supporting operational deployment.

# References
