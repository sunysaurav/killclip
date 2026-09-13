// Apple Vision text recognition for a list of images: one JSON line per image with words and boxes.
import Foundation
import Vision
import AppKit

let args = Array(CommandLine.arguments.dropFirst())
let fast = args.contains("--fast")
let files = args.filter { !$0.hasPrefix("--") }
for f in files {
    guard let img = NSImage(contentsOfFile: f), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("{\"file\":\"\(f)\",\"error\":\"unreadable\"}"); continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = fast ? .fast : .accurate
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    var words: [String] = []
    do {
        try handler.perform([req])
        for obs in req.results ?? [] {
            guard let c = obs.topCandidates(1).first else { continue }
            let b = obs.boundingBox
            let t = c.string.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
            words.append(String(format: "{\"text\":\"%@\",\"x\":%.4f,\"y\":%.4f,\"w\":%.4f,\"h\":%.4f,\"conf\":%.3f}", t, b.minX, 1 - b.maxY, b.width, b.height, c.confidence))
        }
    } catch { words.append("{\"error\":\"\(error)\"}") }
    print("{\"file\":\"\(f)\",\"words\":[\(words.joined(separator: ","))]}")
}
