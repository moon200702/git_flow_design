[Code Commit] 
      │
      ▼
1. Trivy Scans Dockerfile (Fails if insecure)
      │
      ▼
2. Build Container Image
      │
      ▼
3. Trivy Scans Image for CVEs/Secrets (Fails if High/Critical found)
      │
      ▼
4. Deploy Image to Secure Sandbox (gVisor / Isolated Network)
      │
      ▼
5. Run Automated Tests & Monitor Behavior (Falco / Network Logs)
      │
      ▼
[Passes All Tests] ──► Deploy to Production Cluster



[Build Phase] ──► [Registry] ──► [Deploy to Sandbox/Staging] ──► [Production Live]
      │                                    │                             │
   (Trivy)                              (Nmap)                        (Nmap)
Static Scan                          Dynamic Port Scan             Continuous Audit
