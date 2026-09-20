from jev_showdown.telemetry.frames import BattleFrameBuffer


def test_frame_buffer_keeps_only_latest_bounded_frames():
    buffer = BattleFrameBuffer(max_frames=2)
    buffer.start("battle-1")
    buffer.append("battle-1", ["|turn|1"])
    buffer.append("battle-1", ["|turn|2"])
    buffer.append("battle-1", ["|turn|3"])

    assert buffer.replay() == {
        "type": "BATTLE_REPLAY",
        "battle_tag": "battle-1",
        "frames": [["|turn|2"], ["|turn|3"]],
    }


def test_frame_buffer_ignores_frames_for_another_battle():
    buffer = BattleFrameBuffer()
    buffer.start("battle-1")
    buffer.append("battle-2", ["|turn|99"])

    assert buffer.replay() == {
        "type": "BATTLE_REPLAY",
        "battle_tag": "battle-1",
        "frames": [],
    }
