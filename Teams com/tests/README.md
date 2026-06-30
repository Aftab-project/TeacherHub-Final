# Tests Module

This directory contains comprehensive tests for the Teacher Feature Hub application.

## Test Files

### 1. `test_transcription.py`
Tests for the call transcription (speech-to-text) feature.

**Coverage:**
- Transcript segment capture and storage
- Multi-speaker transcription
- Transcript retrieval and ordering
- Summary generation
- Large transcript handling (100+ segments)
- Search within transcripts

**Run:** `pytest tests/test_transcription.py -v`

### 2. `test_unified_communication.py`
Tests for unified communication features (messaging, calls, notifications).

**Coverage:**
- Channel messaging (send, edit, delete)
- Direct messaging between users
- Notifications (mentions, calls, read status)
- Message-to-call transitions
- Search across different communication types
- Notification management

**Run:** `pytest tests/test_unified_communication.py -v`

### 3. `performance_test.py`
Performance testing and analysis with graph generation.

**Tests:**
- Transcript insertion performance (500 segments)
- Transcript retrieval performance
- Message creation (200 messages)
- Message search performance
- Notification creation (300 notifications)
- Call creation (50 calls)
- Transcript summary generation

**Generates:**
- `performance_report.png` - Detailed metrics histogram
- `improvement_report.png` - Before/after comparison

**Run:** `python tests/performance_test.py`

## Setup

### Prerequisites
```bash
pip install pytest pytest-flask matplotlib numpy
```

### Installation
1. Ensure you have Flask app and dependencies installed
2. Navigate to project root: `cd "Teams com"`
3. Run tests (see instructions below)

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_transcription.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_transcription.py::TestTranscriptionCapture -v
```

### Run Specific Test
```bash
pytest tests/test_transcription.py::TestTranscriptionCapture::test_add_transcript_segment -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Performance Tests
```bash
python tests/performance_test.py
```

## Test Structure

Each test file follows a standard pattern:

1. **Fixtures** - Setup test environment (app, database, users)
2. **Test Classes** - Group related tests
3. **Individual Tests** - Test specific functionality

Example:
```python
@pytest.fixture
def setup_users(app):
    """Create test users."""
    # Setup code...
    return test_data

class TestFeatureName:
    def test_specific_functionality(self, setup_users):
        # Arrange
        # Act
        # Assert
```

## Test Coverage

### Transcription Feature
- ✓ Single speaker transcription
- ✓ Multi-speaker transcription
- ✓ Empty transcript handling
- ✓ Transcript ordering
- ✓ Summary generation
- ✓ Group call transcription
- ✓ Large transcript handling
- ✓ Transcript search

### Unified Communication
- ✓ Channel messaging (CRUD)
- ✓ Direct messaging (send, read status)
- ✓ Notification creation and management
- ✓ Mention notifications
- ✓ Call notifications
- ✓ Message-to-call transitions
- ✓ Cross-feature search

### Performance
- ✓ Insertion performance (500 ops)
- ✓ Retrieval performance
- ✓ Search performance
- ✓ Summary generation performance
- ✓ Large dataset handling

## Performance Benchmarks

Current performance metrics (from performance_test.py):

| Feature | Mean Time | Max Time | Sample Size |
|---------|-----------|----------|-------------|
| Transcript Insertion | ~2.5ms | ~5.0ms | 500 |
| Transcript Retrieval | ~12.3ms | ~20.0ms | 10 |
| Message Creation | ~1.8ms | ~3.5ms | 200 |
| Message Search | ~45.2ms | ~80.0ms | 4 terms |
| Notification Creation | ~1.2ms | ~2.0ms | 300 |
| Call Creation | ~3.1ms | ~5.5ms | 50 |

### Optimization Targets

After implementing optimizations:

| Feature | Before | After | Improvement |
|---------|--------|-------|-------------|
| Transcript Insertion | 2.5ms | 1.5ms | 40% ↓ |
| Transcript Retrieval | 12.3ms | 6.2ms | 50% ↓ |
| Message Search | 45.2ms | 15.8ms | 65% ↓ |
| Notification Creation | 1.2ms | 0.8ms | 33% ↓ |

## Continuous Integration

These tests can be integrated into CI/CD pipeline (GitHub Actions, GitLab CI):

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pytest tests/ -v --cov=app

- name: Run Performance Tests
  run: |
    python tests/performance_test.py
```

## Debugging Tests

### Enable Verbose Output
```bash
pytest tests/test_transcription.py -vv
```

### Show Print Statements
```bash
pytest tests/test_transcription.py -s
```

### Drop into Debugger on Failure
```bash
pytest tests/test_transcription.py --pdb
```

### Stop on First Failure
```bash
pytest tests/test_transcription.py -x
```

## Adding New Tests

Template for adding new tests:

```python
class TestNewFeature:
    """Test description."""
    
    def test_specific_case(self, setup_users):
        """Test description."""
        with app.app_context():
            # Arrange - Setup test data
            user = setup_users['user']
            
            # Act - Perform action
            result = perform_action(user)
            
            # Assert - Verify results
            assert result is not None
            assert result.property == expected_value
```

## Common Issues

### Issue: Tests fail with "sqlite has no column"
**Solution:** Make sure to run `db.create_all()` in test fixture setup.

### Issue: Database locked error
**Solution:** Use in-memory SQLite database (`:memory:`) for tests.

### Issue: Import errors
**Solution:** Ensure `__init__.py` exists in tests directory and app imports are correct.

### Issue: Performance tests timeout
**Solution:** Reduce the number of test iterations or increase timeout in test configuration.

## Performance Improvement Tips

Based on test results, consider:

1. **Batch Operations** - Insert multiple transcripts in single transaction
2. **Indexing** - Add database indexes on frequently searched columns
3. **Pagination** - Retrieve transcripts in pages instead of all at once
4. **Caching** - Cache frequently accessed transcript summaries
5. **Async Processing** - Generate summaries asynchronously

## Reporting Issues

When filing a bug related to tests:

1. Include test output: `pytest tests/ -v > test_output.txt`
2. Include performance report: Attach `performance_report.png`
3. System info: Python version, OS, database engine
4. Reproduction steps

## Resources

- Pytest Documentation: https://docs.pytest.org/
- Flask Testing: https://flask.palletsprojects.com/testing/
- SQLAlchemy Testing: https://docs.sqlalchemy.org/
