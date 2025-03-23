'use client'

import { useRef, useEffect, useState } from 'react'

interface CameraProps {
  onPhotoCapture: (photo: string) => void
  photo: string
}

export default function Camera({ onPhotoCapture, photo }: CameraProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [isCameraActive, setIsCameraActive] = useState(false)

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setIsCameraActive(false)
  }

  const initializeCamera = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API is not supported in this browser')
      }

      // First try to access the environment-facing camera
      try {
        const newStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { exact: "environment" } },
          audio: false
        })
        setStream(newStream)
      } catch (envCameraError) {
        // Fall back to any available camera
        const newStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false
        })
        setStream(newStream)
      }

      setIsCameraActive(true)
    } catch (err) {
      let errorMessage = 'Error accessing camera. '
      if (err instanceof Error) {
        switch(err.name) {
          case 'NotAllowedError':
            errorMessage += 'Please grant camera permissions in your browser settings.'
            break
          case 'NotFoundError':
            errorMessage += 'No camera device was found.'
            break
          case 'NotReadableError':
            errorMessage += 'Camera is already in use by another application.'
            break
          default:
            errorMessage += err.message || 'Please ensure you have a working camera.'
        }
      }
      alert(errorMessage)
    }
  }

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current
      const canvas = canvasRef.current
      
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      
      const context = canvas.getContext('2d')
      if (context) {
        context.drawImage(video, 0, 0)
        const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
        onPhotoCapture(dataUrl)
        stopCamera()
      }
    }
  }

  const retakePhoto = () => {
    onPhotoCapture('')
    initializeCamera()
  }

  useEffect(() => {
    if (stream && videoRef.current) {
      videoRef.current.srcObject = stream
    }
  }, [stream])

  return (
    <div className="camera-container mb-4">
      {isCameraActive && (
        <video 
          ref={videoRef} 
          autoPlay 
          playsInline 
          className="w-100"
          style={{ maxWidth: '640px', margin: '0 auto', display: 'block' }}
        />
      )}
      
      {photo && (
        <img 
          src={photo} 
          alt="Captured ingredient list"
          className="w-100"
          style={{ maxWidth: '640px', margin: '0 auto', display: 'block' }}
        />
      )}
      
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      <div className="button-container text-center mt-3">
        {!isCameraActive && !photo && (
          <button 
            className="btn btn-primary" 
            onClick={initializeCamera}
          >
            Start Camera
          </button>
        )}
        
        {isCameraActive && (
          <button 
            className="btn btn-success" 
            onClick={capturePhoto}
          >
            Capture Photo
          </button>
        )}
        
        {photo && (
          <button 
            className="btn btn-secondary" 
            onClick={retakePhoto}
          >
            Retake Photo
          </button>
        )}
      </div>
    </div>
  )
}
