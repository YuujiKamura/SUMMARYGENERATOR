#!/usr/bin/env ruby
# -*- coding: utf-8 -*-

require_relative '../lib/document_ai_client'

# 直接DocumentAI APIテスト
puts "=== DocumentAI直接APIテスト ==="

begin
  client = DocumentAIClient.new
  
  if client.demo_mode
    puts "❌ デモモードです"
    exit 1
  end
  
  puts "✅ 本番モード: DocumentAI APIクライアントが利用可能"
  
  # Python版で使用されている画像を試す
  test_images = [
    'C:\\Users\\yuuji\\Sanyuu2Kouku\\cursor_tools\\summarygenerator\\ocr_tools\\ocr_cache\\8575_cached.jpg',
    'H:\\マイドライブ\\〇東区市道（2工区）舗装補修工事（水防等含）（単価契約）\\６工事写真\\0530小山工区\\RIMG8575.JPG'
  ]
  
  test_images.each do |image_path|
    if File.exist?(image_path)
      puts "\n--- テスト画像: #{File.basename(image_path)} ---"
      
      result = client.extract_text(image_path)
      
      if result['error']
        puts "❌ OCRエラー: #{result['error']}"
      else
        puts "✅ OCR成功!"
        puts "抽出テキスト: #{result['ocr_text']}"
        puts "場所: #{result['location_value']}"
        puts "日付: #{result['date_value']}"
        puts "台数: #{result['count_value']}"
        puts "信頼度: #{result['confidence']}"
      end
      
      break  # 最初に見つかった画像でテスト
    end
  end
  
rescue => e
  puts "❌ エラー: #{e.message}"
  puts e.backtrace.first(3) if ENV['DEBUG']
  exit 1
end
