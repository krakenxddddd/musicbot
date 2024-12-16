set("server.telnet", false)
set("server.socket", true)
settings.server.socket.path.set("/tmp/liquidsoap.sock")

request_queue = request.queue(id="request", timeout=180.)
main_playlist = playlist(mode='randomize', reload=60, "./tracks/")

out = main_playlist #Основной поток по умолчанию

add_skip_command(out)
out = mksafe(out)
out = nrj(out)

ice = output.icecast(%vorbis, id="root", host = "*******", port = 8000, password = "*******", mount = "stream", out)

