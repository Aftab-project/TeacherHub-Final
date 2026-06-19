/**
 * WebRTC Video Call Client
 * 
 * Handles full client-side call behavior:
 * - Captures local audio/video with getUserMedia
 * - Opens signaling channel over Socket.IO
 * - Negotiates WebRTC using SDP offer/answer
 * - Exchanges ICE candidates for NAT traversal
 * - Manages call controls (mute/video/end)
 * - Updates room UI state
 *
 * High-level flow:
 * 1) Page loads with hidden metadata (token, userId, role)
 * 2) Client joins signaling room: socket.emit('join_call', ...)
 * 3) Caller creates offer when participant joins
 * 4) Callee receives offer, creates answer, sends back
 * 5) Both peers exchange ICE candidates
 * 6) Streams attach to <video> tags
 */

class VideoCallClient {
    constructor(callToken, currentUserId, isCaller, callStatus) {
        // Immutable call context from server-rendered hidden inputs
        this.callToken = callToken;
        this.currentUserId = Number(currentUserId);
        this.isCaller = isCaller;
        this.callStatus = callStatus;

        // Runtime WebRTC objects
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = new MediaStream();
        this.socket = null;

        // Prevent duplicate offer sends
        this.offerSent = false;
        
        // STUN servers help peers discover public-facing network addresses
        this.peerConfig = {
            iceServers: [
                { urls: ['stun:stun.l.google.com:19302'] },
                { urls: ['stun:stun1.l.google.com:19302'] }
            ]
        };
        
        // Boot sequence
        this.initializeEventListeners();
        this.initializeSocket();
        this.bootstrapCallState();
    }
    
    /**
     * Initialize DOM event listeners
     */
    initializeEventListeners() {
        // Grab call control buttons if present in current layout
        const acceptBtn = document.getElementById('acceptCall');
        const rejectBtn = document.getElementById('rejectCall');
        const endBtn = document.getElementById('endCall');
        const toggleAudioBtn = document.getElementById('toggleAudio');
        const toggleVideoBtn = document.getElementById('toggleVideo');
        
        // Wire each button to matching class method
        if (acceptBtn) acceptBtn.addEventListener('click', () => this.acceptCall());
        if (rejectBtn) rejectBtn.addEventListener('click', () => this.rejectCall());
        if (endBtn) endBtn.addEventListener('click', () => this.endCall());
        if (toggleAudioBtn) toggleAudioBtn.addEventListener('click', () => this.toggleAudio());
        if (toggleVideoBtn) toggleVideoBtn.addEventListener('click', () => this.toggleVideo());
    }

    /**
     * Initialize Socket.IO signaling channel
     */
    initializeSocket() {
        // Connect to same-origin Socket.IO endpoint
        this.socket = io();

        this.socket.on('connect', () => {
            // Join call-specific room so signaling messages are scoped
            this.socket.emit('join_call', {
                call_token: this.callToken,
                user_id: this.currentUserId
            });
        });

        this.socket.on('participant_joined', async () => {
            // Caller drives initial offer once second participant appears
            if (this.isCaller && this.peerConnection && !this.offerSent) {
                await this.sendOffer();
                this.offerSent = true;
            }
        });

        // Incoming signaling events
        this.socket.on('webrtc_offer', async (data) => {
            await this.handleOffer(data.offer);
        });

        this.socket.on('webrtc_answer', async (data) => {
            await this.handleAnswer(data.answer);
        });

        this.socket.on('ice_candidate', async (data) => {
            await this.handleRemoteCandidate(data.candidate);
        });

        this.socket.on('call_ended', () => {
            // Peer ended call from their side
            alert('The other user ended the call.');
            this.cleanupMedia();
            window.location.href = `/calls/${this.callToken}/summary`;
        });

        this.socket.on('call_error', (data) => {
            console.error('Call signaling error:', data.message);
        });
    }

    /**
     * Bootstrap behavior based on caller/callee state
     */
    async bootstrapCallState() {
        // Caller (or already-active call) should immediately start media and peer setup
        if (this.isCaller || this.callStatus === 'active') {
            await this.startLocalStream();
            await this.createPeerConnection();
            this.updateUI('active');
        }
    }
    
    /**
     * Accept incoming call and start video stream
     */
    async acceptCall() {
        try {
            console.log('Accepting call:', this.callToken);
            
            // Update server status pending -> active
            const response = await fetch(`/calls/${this.callToken}/accept`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to accept call');
            }
            
            // Acquire microphone/camera
            await this.startLocalStream();
            
            // Prepare RTCPeerConnection
            await this.createPeerConnection();
            
            // Switch UI to active-call mode
            this.updateUI('active');

            // Callee waits for offer and responds with answer when received
            
        } catch (error) {
            console.error('Error accepting call:', error);
            alert('Failed to accept call: ' + error.message);
        }
    }
    
    /**
     * Reject incoming call
     */
    async rejectCall() {
        try {
            console.log('Rejecting call:', this.callToken);
            
            await fetch(`/calls/${this.callToken}/reject`, {
                method: 'POST'
            });
            
            // Leave call UI if rejected
            window.location.href = '/team-com/';
            
        } catch (error) {
            console.error('Error rejecting call:', error);
        }
    }
    
    /**
     * End active call
     */
    async endCall() {
        try {
            console.log('Ending call:', this.callToken);
            
            // Stop tracks/peer connection before navigation
            this.cleanupMedia();

            if (this.socket) {
                // Signal peer to end on their side too
                this.socket.emit('end_call_signal', {
                    call_token: this.callToken,
                    sender_id: this.currentUserId
                });
            }
            
            // Persist final call status/duration on backend
            await fetch(`/calls/${this.callToken}/end`, {
                method: 'POST'
            });
            
            // Short delay allows network requests to settle before navigation
            setTimeout(() => {
                window.location.href = `/calls/${this.callToken}/summary`;
            }, 1000);
            
        } catch (error) {
            console.error('Error ending call:', error);
            window.location.href = `/calls/${this.callToken}/summary`;
        }
    }
    
    /**
     * Start local video/audio stream
     */
    async startLocalStream() {
        try {
            console.log('Requesting user media...');
            
            // Ask browser for camera + microphone access
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 } },
                audio: true
            });
            
            // Bind stream to local preview video element
            const localVideo = document.getElementById('localVideo');
            if (localVideo) {
                localVideo.srcObject = this.localStream;
                localVideo.play().catch(e => console.error('Error playing local video:', e));
            }

            // Hide initials placeholder once real video is visible
            const localNoVideo = document.getElementById('localNoVideo');
            if (localNoVideo) {
                localNoVideo.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Error getting user media:', error);
            alert('Unable to access camera/microphone. Please check permissions.');
            throw error;
        }
    }
    
    /**
     * Create peer connection and add local stream
     */
    async createPeerConnection() {
        try {
            console.log('Creating peer connection...');
            
            // RTCPeerConnection coordinates media tracks and ICE state
            this.peerConnection = new RTCPeerConnection(this.peerConfig);
            
            // Publish local tracks (audio/video) to peer connection
            if (this.localStream) {
                this.localStream.getTracks().forEach(track => {
                    this.peerConnection.addTrack(track, this.localStream);
                });
            }
            
            // Fired when remote peer track arrives
            this.peerConnection.ontrack = (event) => {
                console.log('Received remote track:', event.track.kind);
                // Add each remote track to shared MediaStream
                event.streams[0].getTracks().forEach(track => {
                    this.remoteStream.addTrack(track);
                });
                
                const remoteVideo = document.getElementById('remoteVideo');
                if (remoteVideo) {
                    remoteVideo.srcObject = this.remoteStream;
                    remoteVideo.play().catch(e => console.error('Error playing remote video:', e));
                }

                // Hide remote placeholder when stream is ready
                const remoteNoVideo = document.getElementById('remoteNoVideo');
                if (remoteNoVideo) {
                    remoteNoVideo.style.display = 'none';
                }
            };
            
            // Local ICE candidate discovered -> send to peer via signaling server
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    console.log('New ICE candidate:', event.candidate);
                    // Send candidate to peer through signaling server
                    this.sendCandidate(event.candidate);
                }
            };
            
            // Helpful for debugging call connectivity problems
            this.peerConnection.onconnectionstatechange = () => {
                console.log('Connection state:', this.peerConnection.connectionState);
            };
            
        } catch (error) {
            console.error('Error creating peer connection:', error);
            throw error;
        }
    }
    
    /**
     * Create and send SDP offer
     */
    async sendOffer() {
        try {
            console.log('Creating and sending offer...');
            
            // Create SDP offer describing media capabilities
            const offer = await this.peerConnection.createOffer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: true
            });
            
            // Save as local description before sending
            await this.peerConnection.setLocalDescription(offer);
            
            // Send offer to other participant through Socket.IO
            this.socket.emit('webrtc_offer', {
                call_token: this.callToken,
                offer,
                sender_id: this.currentUserId
            });
            
        } catch (error) {
            console.error('Error creating offer:', error);
        }
    }
    
    /**
     * Send ICE candidate to peer
     */
    sendCandidate(candidate) {
        // Candidate routing data so peer can discover viable network path
        this.socket.emit('ice_candidate', {
            call_token: this.callToken,
            candidate,
            sender_id: this.currentUserId
        });
    }

    /**
     * Handle incoming offer and send answer.
     */
    async handleOffer(offer) {
        // Callee may receive offer before local setup is complete
        if (!this.peerConnection) {
            await this.startLocalStream();
            await this.createPeerConnection();
            this.updateUI('active');
        }

        // Accept remote offer -> create + send answer
        await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await this.peerConnection.createAnswer();
        await this.peerConnection.setLocalDescription(answer);

        this.socket.emit('webrtc_answer', {
            call_token: this.callToken,
            answer,
            sender_id: this.currentUserId
        });
    }

    /**
     * Handle incoming answer from peer.
     */
    async handleAnswer(answer) {
        // Caller receives answer and finalizes negotiation
        if (!this.peerConnection) {
            return;
        }
        await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    }

    /**
     * Add received ICE candidate.
     */
    async handleRemoteCandidate(candidate) {
        // Add peer ICE candidates as they arrive
        if (!this.peerConnection) {
            return;
        }
        try {
            await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (error) {
            console.error('Error adding remote ICE candidate:', error);
        }
    }

    /**
     * Stop streams and close connection objects.
     */
    cleanupMedia() {
        // Stop local camera/mic tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        // Close RTCPeerConnection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        // Disconnect signaling socket
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }
    
    /**
     * Toggle audio (mute/unmute)
     */
    toggleAudio() {
        if (this.localStream) {
            const audioTracks = this.localStream.getAudioTracks();
            // Flip enabled flag on each audio track
            audioTracks.forEach(track => {
                track.enabled = !track.enabled;
            });
            
            // Update button label to reflect current state
            const btn = document.getElementById('toggleAudio');
            if (btn) {
                btn.textContent = audioTracks[0].enabled ? '🎤 Mute' : '🎤 Unmute';
            }
        }
    }
    
    /**
     * Toggle video (on/off)
     */
    toggleVideo() {
        if (this.localStream) {
            const videoTracks = this.localStream.getVideoTracks();
            // Flip enabled flag on each video track
            videoTracks.forEach(track => {
                track.enabled = !track.enabled;
            });
            
            // Update button label to reflect current state
            const btn = document.getElementById('toggleVideo');
            if (btn) {
                btn.textContent = videoTracks[0].enabled ? '📹 Stop' : '📹 Start';
            }
        }
    }
    
    /**
     * Update UI based on call state
     */
    updateUI(state) {
        // Cache relevant controls
        const acceptBtn = document.getElementById('acceptCall');
        const rejectBtn = document.getElementById('rejectCall');
        const endBtn = document.getElementById('endCall');
        const controlsDiv = document.getElementById('callControls');
        const pendingControls = document.getElementById('pendingControls');
        
        if (state === 'active') {
            // Hide incoming-call controls
            if (acceptBtn) acceptBtn.style.display = 'none';
            if (rejectBtn) rejectBtn.style.display = 'none';
            if (pendingControls) pendingControls.style.display = 'none';

            // Show active-call controls
            if (endBtn) endBtn.style.display = 'inline-block';
            if (controlsDiv) controlsDiv.style.display = 'block';

            // Visual status badge update
            const statusBadge = document.getElementById('statusBadge');
            if (statusBadge) {
                statusBadge.textContent = 'Active';
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Read server-provided hidden metadata fields
    const callTokenElement = document.getElementById('callToken');
    const currentUserIdElement = document.getElementById('currentUserId');
    const isCallerElement = document.getElementById('isCaller');
    const callStatusElement = document.getElementById('callStatus');

    if (callTokenElement) {
        // Parse values into expected types
        const callToken = callTokenElement.value;
        const currentUserId = currentUserIdElement ? currentUserIdElement.value : '0';
        const isCaller = isCallerElement ? isCallerElement.value === 'true' : false;
        const callStatus = callStatusElement ? callStatusElement.value : 'pending';
        // Create globally reachable client for debugging from browser console
        window.videoClient = new VideoCallClient(callToken, currentUserId, isCaller, callStatus);
    }
});
