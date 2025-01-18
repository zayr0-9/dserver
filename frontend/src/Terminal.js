import React, {useState, useEffect, useRef} from "react";
import{ useXTerm} from "react-xtermjs";

const MyTerminal = ({ wsEndpoint, initialPath }) => {
    const { instance, ref } = useXTerm();

    useEffect(() => {
        const socket = new WebSocket(wsEndpoint);

        socket.onopen = () => {
            instance?.writeln(`Connected to ${wsEndpoint}`);
            instance?.writeln(`Starting in directory: ${initialPath}`);
        };

        socket.onmessage = (event) => {
            instance?.write(event.data);
        };

        instance?.onData((data) => {
            socket.send(data);
        });

        return () => {
            socket.close();
        };
    }, [wsEndpoint, initialPath, instance]);

    return (
        <div>
            ref={ref}
        </div>
    )
};

export default MyTerminal;