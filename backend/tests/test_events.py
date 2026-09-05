from engine.events import detect_events, primary_event


def test_request_photo():
    assert detect_events("发张照片看看")["request_photo"] is True
    assert detect_events("看看你长啥样")["request_photo"] is True
    assert detect_events("再发一张嘛，没看够")["request_photo"] is True
    assert detect_events("再来一张自拍呗")["request_photo"] is True
    assert detect_events("多发几张照片")["request_photo"] is True
    assert detect_events("来张照片给我看看")["request_photo"] is True


def test_doubt_ai():
    assert detect_events("你是机器人吧")["doubt_ai"] is True
    assert detect_events("你是不是ai")["doubt_ai"] is True


def test_red_packet():
    assert detect_events("给你发了红包")["red_packet"] is True
    assert detect_events("转账给你啦")["red_packet"] is True


def test_buy_intent():
    assert detect_events("这个茶叶多少钱")["buy_intent"] is True


def test_casual_has_no_event():
    ev = detect_events("在吗 在干嘛呢")
    assert primary_event(ev) == "casual"
