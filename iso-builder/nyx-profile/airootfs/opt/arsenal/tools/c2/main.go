package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"time"
)

// Configure the Two-Model Local Consensus Network
const (
	AnalyzerBrain  = "gemma2:2b"     // Google's code-syntax expert
	CommanderBrain = "granite3.3:2b" // IBM's security decision engine
)

type SecurityLog struct {
	PID            uint32 `json:"pid"`
	PPID           uint32 `json:"ppid"`
	UID            uint32 `json:"uid"`
	ParentProcess  string `json:"parent_process"`
	BinaryExecuted string `json:"binary_executed"`
}

type OllamaRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

type OllamaResponse struct {
	Response string `json:"response"`
}

// CleanAIResponse strips away intermediate reasoning/thinking tags from local models
func CleanAIResponse(rawResponse string) string {
	if strings.Contains(rawResponse, "</thought>") {
		parts := strings.Split(rawResponse, "</thought>")
		return strings.TrimSpace(parts[len(parts)-1])
	}
	return strings.TrimSpace(rawResponse)
}

// QueryOllama Engine speaks directly to your local loopback Ollama service
func QueryOllama(model string, prompt string) (string, error) {
	requestBody, err := json.Marshal(OllamaRequest{
		Model:  model,
		Prompt: prompt,
		Stream: false,
	})
	if err != nil {
		return "", err
	}

	resp, err := http.Post("http://127.0.0", "application/json", bytes.NewBuffer(requestBody))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var ollamaResp OllamaResponse
	if err := json.Unmarshal(body, &ollamaResp); err != nil {
		return "", err
	}

	return CleanAIResponse(ollamaResp.Response), nil
}

// RunConsensusLoop routes telemetry through Gemma, then feeds the report into Granite
func RunConsensusLoop(secLog SecurityLog) {
	// --- PHASE 1: GEMMA 2 2B TECHNICAL DECONSTRUCTION ---
	gemmaPrompt := fmt.Sprintf(
		"You are a neutral code analyzer. Describe strictly what this execution context does without judging if it is malicious or safe.\n"+
			"Parent Process: %s\nExecuted Command: %s\nUser Context ID: %d\nProvide a technical summary in one sentence:",
		secLog.ParentProcess, secLog.BinaryExecuted, secLog.UID,
	)

	gemmaReport, err := QueryOllama(AnalyzerBrain, gemmaPrompt)
	if err != nil {
		log.Printf("[!] Phase 1 (Gemma) Failed: %v", err)
		return
	}
	fmt.Printf("\n[🔬 GEMMA ANALYSIS]: %s\n", gemmaReport)

	// --- PHASE 2: GRANITE 3.3 2B SECURITY COMMAND VERDICT ---
	granitePrompt := fmt.Sprintf(
		"You are Cerberus-Commander, an automated endpoint defense coordinator. Read this system event profile and the technical analysis report.\n\n"+
			"Event Profile:\n- Binary Path: %s\n- User ID: %d\n\nTechnical Analysis:\n%s\n\n"+
			"Determine if this is a hostile attack or unauthorized privilege escalation. You must end your response with exactly 'VERDICT: KILL' or 'VERDICT: ALLOW':",
		secLog.BinaryExecuted, secLog.UID, gemmaReport,
	)

	graniteVerdict, err := QueryOllama(CommanderBrain, granitePrompt)
	if err != nil {
		log.Printf("[!] Phase 2 (Granite) Failed: %v", err)
		return
	}
	fmt.Printf("[⚔️ GRANITE COMMAND]: %s\n\n", graniteVerdict)
}

// MonitorRustAgent watches the background process. If it drops out, it resurrects it instantly.
func MonitorRustAgent() {
	log.Println("[🛡️ IMMORTAL CAPABILITY] Watchdog thread online. Securing Rust Agent heartbeat...")
	
	for {
		// Check if the cerberus-agent process is currently running on the Linux system
		cmd := exec.Command("pgrep", "-f", "cerberus-agent")
		err := cmd.Run()
		
		// If pgrep exits with an error code, it means the binary was killed or crashed
		if err != nil {
			log.Println("[!] CRITICAL CRASH DETECTED: Cerberus Agent has been terminated! Resurrecting head...")
			
			// Re-launch the compiled Rust agent instantly back into kernel tracking space
			resurrect := exec.Command("sudo", "../../cmd/agent/target/release/cerberus-agent")
			resurrect.Stdout = os.Stdout
			resurrect.Stderr = os.Stderr
			
			if err := resurrect.Start(); err != nil {
				log.Printf("[!] Watchdog resurrection failure: %v", err)
			} else {
				log.Println("[+] Sibling resurrected successfully. Perimeter defense restored.")
			}
		}
		
		// Pulse-check every 500 milliseconds to avoid grinding system CPU resources
		time.Sleep(500 * time.Millisecond)
	}
}

func main() {
	log.Println("[+] Cerberus Command Tower (Right Head) waking up...")
	log.Println("[+] Multi-Model Consensus Engine initialized on port 8080...")

	// Launch the unkillable watchdog routine asynchronously
	go MonitorRustAgent()

	http.HandleFunc("/telemetry", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Invalid method", http.StatusMethodNotAllowed)
			return
		}

		var secLog SecurityLog
		if err := json.NewDecoder(r.Body).Decode(&secLog); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// Process the consensus reasoning asynchronously so your kernel data loop never pauses
		go RunConsensusLoop(secLog)

		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"received"}`))
	})

	if err := http.ListenAndServe("127.0.0.1:8080", nil); err != nil {
		log.Fatalf("[!] Command Tower network pipeline dropped: %v", err)
	}
}
