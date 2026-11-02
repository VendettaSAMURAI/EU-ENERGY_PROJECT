# Project Requirements: Data Visualization Methods (INMAA0105L-01/26f)

Source: course page "Requirements for the project work", University of Debrecen e-learning.
This is the official assignment brief. All design and implementation decisions should be checked against it.

## Project Work
Students are required to create an **interactive data visualization dashboard** using a freely chosen dataset.

The purpose of the dashboard is to effectively support the **exploration and analysis** of the selected dataset; therefore, simply displaying static charts is not sufficient.

## Minimum Requirements
The dashboard should:
- contain **several types of meaningful data visualizations**;
- include **interactive features that support data analysis**, such as filtering, searching, selection, hover information, zooming, or linked views;
- allow users to **examine the data from different perspectives**;
- use **at least one visualization library listed on PyViz.org**;
- **not rely exclusively on traditional bar, line, and pie charts**.

Chart types should always be selected according to the characteristics of the data and the analytical questions being investigated. **Variety is not a goal in itself**: the visualizations should support the analysis and interpretation of the data.

## Data Preparation
Data preparation is an important part of the project. This may include, for example:
- cleaning the data;
- handling missing or erroneous values;
- converting data types;
- creating categories or derived variables;
- aggregating data;
- combining multiple data sources;
- restructuring the data into a format suitable for visualization.

**The source of the dataset must be clearly indicated.**

## Assessment Criteria
| Criterion | What is assessed |
|---|---|
| **Data Preparation** | The extent and quality of the data processing and preparation carried out on the selected dataset. |
| **Design Process** | The overall structure and coherence of the dashboard, the clarity of the analytical questions, and the consistency of the visual design. |
| **Quality of Visualizations** | The appropriate choice of visualization types, their readability, visual quality, and diversity. |
| **Analytical Capabilities** | The usefulness of filtering, searching, selection, and other interactive features, and the extent to which the dashboard supports meaningful exploration and comparison of the data. |
| **Technical Implementation** | The functionality and stability of the dashboard, and the appropriate use of the selected visualization library or libraries. |
| **Project Presentation / Defense** | See below. |

## Project Presentation / Defense
Each student should be able to:
- present the dataset;
- explain the main steps of data preparation;
- describe the most important design decisions;
- demonstrate how the dashboard works;
- discuss the key insights that can be derived from the visualizations.

During the presentation, the student should **formulate the most important analytical questions** the dashboard is designed to address and **demonstrate how the visualizations and interactive features support the investigation of these questions**.

## Examples
Provided by the course: http://tinyurl.com/5fy3ehwm and http://tinyurl.com/npdcpjrh

---

## Guidance for the assistant
When proposing or reviewing work, check it against this brief:
- Every chart must serve a stated analytical question. Do not add chart types just for variety.
- Prefer chart types beyond bar/line/pie where the data supports it (heatmaps, area/stream, distributions, maps, scatter with brushing, duration curves).
- Interactivity must aid analysis (filtering, linked selection, comparison), not decoration.
- Every data preparation step should be scripted, reproducible from `data/raw/`, and documented in `docs/` so it can be explained in the defense.
- Data sources and licences must be cited in the README and in the dashboard itself (e.g. an "About the data" tab).
- Stability matters: the dashboard must run reliably with `panel serve dashboard/app.py`.
- Follow the working preferences in `CLAUDE.md`.