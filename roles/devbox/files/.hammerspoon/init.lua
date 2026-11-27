local inputSource = require("modules.input_source")
inputSource.start()

-- local hyper = require("modules.hyper")
-- hyper.start()

local bar = require("modules.bar")
bar.start()
hs.shutdownCallback = bar.stop

require("modules.reload_watcher").start()
