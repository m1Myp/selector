# Selector

**Selector** is a tool for decomposing a target profile into a weighted sum of unit test profiles. It is implemented as a pipeline consisting of four scripts.

## 📦 Project Structure

```
selector/
├── stage1/    
│       └── find_files.py           # Search and organize source profiles
├── stage2/
│       ├── build_histo.py          # Convert source profiles into internal representation (histograms), compression
│       ├── JFRParser.java          # Executable Java file implementing the algorithm to convert JFR files into histograms used in the histogram building stage
│       └── input_file_schema.json  # Schema for validating input file for build_histo.py
├── stage3/
│       ├── solve_math.py           # Solve the decomposition problem in terms of histograms
│       └── input_file_schema.json  # Schema for validating input file for solve_math.py
├── stage4/
│       ├── postprocess.py          # Generate the final set of artifacts
│       └── input_file_schema.json  # Schema for validating input file for postprocess.py
├── utils/
│       └── utils.py                # Contains functions used across multiple files at various stages
```

## 🚀 Quick Start

### 1. Set Environment Variables

```bash
# Base
export TOOL_DIR="$(pwd)/tools"                # Directory where scripts are stored
export WORK_DIR="$(pwd)/work_dir"             # Directory for current and output artifacts
export SAMPLE_DIR="/home/user/profiles"       # All profiles except target ones are considered unit test profiles (stage 1)
export REFERENCE_DIR="$SAMPLE_DIR/reference"  # This directory should contain exactly one profile, which is the target (stage 1)
# Advanced (have defaults)
export LOOKUP_MASK="*.jfr"                    # Mask identifying profiles (stage 1)
export BLOCK_COMPRESSION=true                 # Whether to compress consecutive identifiers with the same value into blocks (stage 2)
export HOTNESS_COMPRESSION=97                 # Percentage of the hottest identifiers to keep when compressing profiles (stage 2) 
export MIN_SIMILARITY=95                      # Minimum target similarity percentage (stage 3)
export MAX_SELECTED_SAMPLES=5                 # Maximum number of unit tests to select (stage 3)
export TIME_LIMIT_SECONDS=60                  # Time limit for solving the optimization problem (stage 3)
export THREADS_COUNT=4                        # Number of threads for parallel linear programming (stage 3) 
export REFERENCE_ARTIFACT_DEPTH=2             # How many directories up from the reference file to copy artifacts (stage 4) 
export SAMPLE_ARTIFACT_DEPTH=2                # How many directories up from sample files to copy artifacts (stage 4) 
```

### 2. Prepare Environment
```bash
mkdir -p $TOOL_DIR
mkdir -p $WORK_DIR
git clone https://github.com/m1Myp/selector.git $TOOL_DIR
pip install -r $TOOL_DIR/selector/requirements.txt
```

### 3. Execute Pipeline Steps Sequentially

```bash
python3 $TOOL_DIR/stage1/find_files.py                    \
    --sample-dir=$SAMPLE_DIR                              \
    --reference-dir=$REFERENCE_DIR                        \
    --lookup-mask=$LOOKUP_MASK                            \
    --work-dir=$WORK_DIR
    
python3 $TOOL_DIR/stage2/build_histo.py                   \
    --block-compression=$BLOCK_COMPRESSION                \
    --hotness-compression=$HOTNESS_COMPRESSION            \
    --work-dir=$WORK_DIR

python3 $TOOL_DIR/stage3/solve_math.py                    \
    --min-similarity=$MIN_SIMILARITY                      \
    --max-selected-samples=$MAX_SELECTED_SAMPLES          \
    --time-limit-seconds=$TIME_LIMIT_SECONDS              \
    --threads-count=$THREADS_COUNT                        \
    --work-dir=$WORK_DIR

python3 $TOOL_DIR/stage4/postprocess.py                   \
    --reference-artifact-depth=$REFERENCE_ARTIFACT_DEPTH  \
    --sample-artifact-depth=$SAMPLE_ARTIFACT_DEPTH        \
    --work-dir=$WORK_DIR
```

## 🔍 What Each Stage Does?

### 🔹 Stage 1: `find_files.py`
This script finds all profile files matching the $LOOKUP_MASK pattern. It classifies them as reference or sample and saves the information in JSON.

Example output JSON structure:
```json
[
  {
    "type": "reference",
    "source_file": "/home/user/profiles/reference/profile.jfr"
  },
  {
    "type": "sample",
    "source_file": "/home/user/profiles/sample1/profile.jfr"
  }
]
```
The script first identifies the reference file, then finds all sample files (everything that's not reference) and saves their paths to `$WORK_DIR/stages/files.json`.

### 🔹 Stage 2: `build_histo.py`
Converts the found profile files into histogram format for further processing. The script doesn't generate histograms but extracts them from profiles and saves them in a JSON file.

Compression is configured via command-line parameters:

- `$BLOCK_COMPRESSION`: Whether to compress consecutive identifiers with the same call count into blocks (default `true`).

- `$HOTNESS_COMPRESSION`: Percentage of the hottest identifiers to keep when compressing profiles (default `97`).

#### Supported Input File Formats

The following input file types are supported:

- `.jfr` — Java Flight Recorder files 
- `.histo` — pre-generated histograms
- `.???` — to support new formats, implement `build_from_???()` and add it to `build_histo_from_profile()`

#### Histogram Structure

Each histogram in the JSON file represents a pair of "identifier - call count".

Example histogram structure:

```json
{
  "histo": {
    "id1": 6,
    "id2": 3,
    "id3": 1
  }
}
```

#### Output Files

The script saves results in JSON format to `$WORK_DIR/stages/histos.json`. 

Example output JSON structure:

```json
[
  {
    "type": "reference",
    "source_file": "/home/user/profiles/reference/profile.jfr",
    "histo": {
      "id1": 6,
      "id2": 3,
      "id3": 1
    }
  },
  {
    "type": "sample",
    "source_file": "/home/user/profiles/sample1/profile.jfr",
    "histo": {
      "id1": 1,
      "id2": 2,
      "id3": 3
    }
  }
]
```

#### Histogram Compression

Histogram compression reduces data size, speeding up `solve_math.py`. 

**Hotness Compression** keeps only the top `N` percent of the hottest (most frequently used) identifiers. This means identifiers with the lowest usage frequency are excluded from analysis.

Default is `97%`. This retains identifiers that most impact program execution while removing insignificant data.

**Block Compression** compresses consecutive identifiers with the same call count into blocks, replacing their values with the sum of calls in the block. Importantly, identifier blocks must be replaced identically across all histograms.

Default is `true`. This reduces the number of identifiers by mutually replacing them with blocks.

Example of **Block Compression**:

If a histogram contains identifiers with identical values (e.g.,`id1`, `id2`, `id3` with the same call count), they are compressed into one block with summed values.

For example, if the histogram is:

```
id1 2
id2 2
id3 2
```

After block compression:

```
id1 6
```

However, blocks must be replaceable identically across all files.

If in one file the identifier blocks `id1`, `id2`, `id3` have the same values, but in another file these block components have different values or are missing, then compression will not occur. For example, if in another file:
  ```
  id1 1
  id2 2
  id3 3
  ```
  or
  ```
  id1 2
  id3 2
  ```
then no compression will happen because the blocks cannot be merged across all files due to mismatched values or missing identifiers.

However, if in all files the identifier blocks are present with the same values, or if all the identifiers that make up the block are missing at once, then block compression will proceed correctly. For example, if the second file contains:
  ```
  id1 8
  id2 8
  id3 8
  ```
then the replacement will work correctly, and the resulting histogram will be:
```
id1 24
```

### 🔹 Stage 3:  `solve_math.py`

This script solves the mathematical part of the problem using linear programming with binary variables.

Parameters:

- `$MAX_SELECTED_SAMPLES`: Maximum number of sample files to select (default `5`)

- `$MIN_SIMILARITY`: Minimum similarity percentage for selecting sample files (default `95`)

- `$TIME_LIMIT_SECONDS`: Maximum time in seconds for the linear programming algorithm (default`60`)

- `$THREADS_COUNT`: Number of threads for parallel linear programming (default `4`)

The goal is to select a number of sample files (not exceeding `MAX_SELECTED_SAMPLES`)  with weights such that the similarity of the weighted sum to the target profile reaches `MIN_SIMILARITY`. 
If the required similarity isn't achieved, the maximum possible number of sample files is selected, and the highest possible similarity is determined.

After execution, the script generates a file with weights for selected samples `$WORK_DIR/stages/weight.json` and the final similarity of the decomposition.

Example output JSON structure:
```json
{
  "reference_file": "/home/user/profiles/reference/profile.jfr",
  "similarity": 98,
  "selected_samples": [
    {
      "sample_path": "/home/user/profiles/sample1/profile.jfr",
      "weight": 0.33
    },
    {
      "sample_path": "/home/user/profiles/sample2/profile.jfr",
      "weight": 0.67
    },
  ]
}
```
#### Mathematical Problem Formulation

The optimization problem minimizes deviations between the weighted sum of test histograms and the target histogram. Let:

- $` ID = \{id_1, id_2, \dots, id_n\} `$ be the set of all encountered identifiers.

- $` S = \{s_1, s_2, ..., s_n\} `$ be the set of vector histograms of the sample files. Each element of the test histogram vector $` s_i `$ is a vector of numbers $` s_i = [s_{i1}, s_{i2}, ..., s_{in}] `$ with real values $` s_{ij} \in \mathbb{R} `$.

- $` T = [t_1, t_2, ..., t_n] `$ is the target vector histogram. Each element $` t_j \in \mathbb{R} `$ represents the target value for the $` j `$-th feature.

The elements $` t_j `$ and $` s_{ij} `$ correspond one-to-one to the set $` ID `$, meaning that for each $` j `$ in $` T `$ and each $` i `$, $` j `$ in $` S `$, there exists a unique correspondence $` t_j \leftrightarrow id_j `$ and $` s_{ij} \leftrightarrow id_j `$, where the $` j `$-th element of histogram $` T `$ and $` s_{ij} `$ from histogram $` s_i `$ both correspond to the same identifier $` id_j \in ID `$. 

- $` w = [w_1, w_2, ..., w_n] `$ are the weights of the tests that are optimized. Each weight is a real number.

- $` z = [z_1, z_2, ..., z_n] `$ are binary variables, where:
  - $` z_i \in \{0, 1\} `$
  - $` z_i = 1 `$ means test $` i `$ is selected
  - $` z_i = 0 `$ means test $` i `$ is not selected

##### Objective Function:

Minimize deviation between weighted sum of tests and target histogram:

$$
\text{minimize} \quad \sum_{i=1}^{n} \left| w_i \cdot s_i - T \right|
$$

where $` w_i \cdot s_i `$ is the weighted sum of the tests, and $` T `$ is the target histogram.

##### Constraints:

- Weight constraint:
  $`
  w_i \geq 0, \quad \forall i
  `$
  
- Weight normalization:
  $`
  \sum_{i=1}^{n} w_i = 1
  `$

- Binary variables:
  $`
  w_i \leq z_i, \quad \forall i
  `$

  Weight $` w_i `$ can only be positive if the test is selected (i.e., $` z_i = 1 `$).

- Maximum selected tests:
  $`
  \sum_{i=1}^{n} z_i \leq \text{max\_selected\_samples}
  `$

### 🔹 Stage 4: `postprocess.py`

Based on `weight.json`, this script copies artifacts to final directories and creates a weight file.

Parameters:

- `$REFERENCE_ARTIFACT_DEPTH`: How many directories up from reference files to copy artifacts (default `2`)

- `$SAMPLE_ARTIFACT_DEPTH`: How many directories up from sample files to copy artifacts (default `2`)

Depth values:

- `0`: Copy only the profile file
- `1 и далее`: Copy the directory with all files at the specified depth from the profile file

The script creates a weight file and copies the directory containing the reference profile with all contents at depth `$REFERENCE_ARTIFACT_DEPTH`, as well as directories containing selected sample profiles with all contents at depth `$SAMPLE_ARTIFACT_DEPTH`.

```
work_dir/
├── weight
├── reference/
│       ├── profile.jfr
│       └── artifact1
├── sample1/
│       ├── profile.jfr
│       ├── artifact_folder1/
│       │       └── artifact2
├── sample2/
│       ├── profile.jfr
│       └── artifact_folder2/
```

The `weight` file contains pairs of "folder name in `$WORK_DIR/` - weight of the test profile inside this folder".

Example `weight` file:

```
sample1 0.33
sample2 0.67
```

## 🧪 Example Input Structure
```
profiles/
├── reference/
│       ├── profile.jfr
│       └── artifact1
├── sample1/
│       ├── profile.jfr
│       ├── artifact_folder1/
│       │       └── artifact2
├── sample2/
│       ├── profile.jfr
│       └── artifact_folder2/
```

## 💡 Features

- Ability to run each step separately
- Histogram compression support
- JSON formats for intermediate data

## 🛠️ Debugging

For debugging, use these flags:
- `--debug`: shows full stack trace on any error (all stages)
- `--verbose`: displays logs of the mathematical solution (stage 3)

## 📧 Feedback

Development: **Timur Ilinykh**  
With support from **Dmitrii Silin**, **Ilya Matveev**

Telegram: **@ElfHunterAO**

Email: **timm00100@gmail.com**
