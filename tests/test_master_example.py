import os
import tempfile

from langflow.schema.data import Data
from langflow.schema.message import Message

from components.helpers.master_example import MasterExample


def test_build_message_basic():
    c = MasterExample()
    c.title = "Unit Test"
    c.notes = "Hello"
    c.enabled = True
    c.items = ["one", "two"]
    msg = c.build_message()
    assert isinstance(msg, Message)
    assert "Unit Test" in str(msg.text)
    assert "Items: one, two" in str(msg.text)
    assert "Built Message output." in str(c.status)


def test_build_data_and_dataframe():
    c = MasterExample()
    c.items = ["a", "b", "c"]
    d = c.build_data()
    assert isinstance(d, Data)
    assert d.data["items"] == ["a", "b", "c"]
    df = c.build_dataframe()
    # Latest LangFlow may not expose DataFrame; component returns Data with rows
    if isinstance(df, Data):
        rows = df.data["rows"]
        assert len(rows) == 3
        assert {r["item"] for r in rows} == {"a", "b", "c"}
    else:
        # Best-effort for DataFrame-like object
        try:
            length = len(df)  # type: ignore[arg-type]
            items = set(df["item"].tolist())  # type: ignore[index]
            assert length == 3
            assert items == {"a", "b", "c"}
        except Exception as exc:
            raise AssertionError("Unexpected dataframe output shape") from exc


def test_file_read_and_tags():
    c = MasterExample()
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write("file contents here")
        path = f.name
    try:
        c.file = path
        c.tags = "alpha, beta , gamma"
        msg = c.build_message()
        assert "file contents here" in msg.text
        assert "Tags: alpha, beta, gamma" in msg.text
    finally:
        os.unlink(path)


message_basic_disabled_short_circuit = None


def test_disabled_short_circuit():
    c = MasterExample()
    c.enabled = False
    msg = c.build_message()
    assert "(MasterExample disabled)" in str(msg.text)
    assert "Disabled; emitted placeholder message." in str(c.status)
