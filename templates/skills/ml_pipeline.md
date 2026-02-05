### model-performance-analyzer
Analyze model metrics and suggest improvements.

**When to use:**
- Training plateaus
- Inference too slow
- Poor generalization

### data-pipeline-optimizer
Optimize data loading and preprocessing.

**When to use:**
- Training bottlenecked by data
- Memory issues

**Output:** Profiling report + optimization suggestions

### video-processing-optimizer
Analyze and optimize video processing pipelines.

**When to use:**
- Slow frame extraction
- High memory usage during processing
- Batch processing bottlenecks

**Checks:**
- ffmpeg parameters (codec, quality, threading)
- Frame sampling strategy
- Parallel processing opportunities

**Tools:** ffmpeg, profiler

### broadcast-segmentation-analyzer
Evaluate scene segmentation quality.

**When to use:**
- Segments too short/long
- Missing scene boundaries
- False positive splits

**Metrics:** 
- Boundary precision/recall
- Segment duration distribution
- Visual/audio change correlation

### embedding-quality-tester
Test and compare embedding models for search.

**When to use:**
- Evaluating new embedding models
- Search quality issues
- Need domain-specific embeddings

**Output:** Comparison report + recommendations
