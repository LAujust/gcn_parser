import json
import pytest
import requests
from unittest.mock import patch, MagicMock

from gcn_parser.extractor import (
    _extract_json,
    _extract_json_array,
    extract_circular,
    extract_circulars_batch,
)


class TestExtractJson:
    def test_plain_json(self):
        raw = '{"event_type": "GRB"}'
        assert _extract_json(raw) == {"event_type": "GRB"}

    def test_markdown_fence(self):
        raw = "```json\n{\"event_type\": \"GRB\"}\n```"
        assert _extract_json(raw) == {"event_type": "GRB"}

    def test_markdown_fence_no_lang(self):
        raw = "```\n{\"event_type\": \"GRB\"}\n```"
        assert _extract_json(raw) == {"event_type": "GRB"}

    def test_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("not json")


class TestExtractJsonArray:
    def test_array(self):
        raw = '[{"gcn_number": "123"}]'
        assert _extract_json_array(raw) == [{"gcn_number": "123"}]

    def test_not_array(self):
        with pytest.raises(ValueError, match="Expected JSON array"):
            _extract_json_array('{"gcn_number": "123"}')


class TestExtractCircular:
    @patch("gcn_parser.extractor.requests.post")
    @patch("gcn_parser.extractor._api_key", return_value="fake-key")
    def test_success(self, mock_key, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"event_type": "GRB"}'}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = extract_circular("raw text", api_key="fake-key")
        assert result.event_type == "GRB"

    @patch("gcn_parser.extractor.requests.post")
    @patch("gcn_parser.extractor._api_key", return_value="fake-key")
    def test_retry_on_429(self, mock_key, mock_post):
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 429
        err = requests.HTTPError("429")
        err.response = mock_resp_fail
        mock_resp_fail.raise_for_status.side_effect = [
            err,
            None,
        ]
        mock_resp_fail.json.return_value = {
            "choices": [{"message": {"content": '{"event_type": "GRB"}'}}]
        }

        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = {
            "choices": [{"message": {"content": '{"event_type": "GRB"}'}}]
        }
        mock_resp_ok.raise_for_status = MagicMock()

        mock_post.side_effect = [mock_resp_fail, mock_resp_ok]

        result = extract_circular("raw text", api_key="fake-key")
        assert result.event_type == "GRB"
        assert mock_post.call_count == 2

    @patch("gcn_parser.extractor.requests.post")
    @patch("gcn_parser.extractor._api_key", return_value="fake-key")
    def test_empty_choices(self, mock_key, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="no choices"):
            extract_circular("raw text", api_key="fake-key")


class TestExtractCircularsBatch:
    @patch("gcn_parser.extractor.requests.post")
    @patch("gcn_parser.extractor._api_key", return_value="fake-key")
    def test_success(self, mock_key, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                {"gcn_number": "GCN 1", "event_type": "GRB"},
                                {"gcn_number": "GCN 2", "event_type": "SGRB"},
                            ]
                        )
                    }
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        circulars = [
            {"gcn": "GCN 1", "text": "text1"},
            {"gcn": "GCN 2", "text": "text2"},
        ]
        result = extract_circulars_batch(circulars, api_key="fake-key")
        assert len(result) == 2
        assert result[0]["gcn_number"] == "GCN 1"

    @patch("gcn_parser.extractor.requests.post")
    @patch("gcn_parser.extractor._api_key", return_value="fake-key")
    def test_length_mismatch(self, mock_key, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([{"gcn_number": "GCN 1"}])
                    }
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        circulars = [
            {"gcn": "GCN 1", "text": "text1"},
            {"gcn": "GCN 2", "text": "text2"},
        ]
        with pytest.raises(RuntimeError, match="expected 2"):
            extract_circulars_batch(circulars, api_key="fake-key")

    def test_empty_input(self):
        assert extract_circulars_batch([]) == []
