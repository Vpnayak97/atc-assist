from app.core import phraseology as ph


def test_callsigns():
    assert ph.callsign_speech("AIC101") == "Air India one zero one"
    assert ph.callsign_speech("IGO612C") == "IndiGo six one two charlie"
    assert ph.callsign_speech("VTCSP") == "victor tango charlie sierra papa"


def test_numbers():
    assert ph.heading_speech(270) == "two seven zero" and ph.heading_speech(5) == "zero zero five"
    assert ph.heading_speech(0) == "three six zero"
    assert ph.altitude_words(4500) == "four thousand five hundred" and ph.altitude_words(11000) == "one one thousand"
    assert ph.level_speech(18000, 4000) == "flight level one eight zero"
    assert ph.level_speech(4000, 4000) == "altitude four thousand feet"


def test_instruction_text():
    own = dict(hex="a", callsign="AIC101", reg=None, x=0, y=0, trk=90.0, alt=10000.0)
    other = dict(hex="b", callsign="IGO612C", reg=None, x=10, y=0, trk=270.0, alt=10000.0)
    text, short = ph.build_instruction({"kind": "level", "value": 8000.0}, own, other, 4000.0)
    assert text.startswith("Air India one zero one, descend flight level eight zero.")
    assert "3 o'clock" in text and "10 miles" in text and "same level" in text and short == "AIC101 DESCEND FL080"