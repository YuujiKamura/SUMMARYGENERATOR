#!/usr/bin/env ruby
# -*- coding: utf-8 -*-

require_relative '../lib/document_ai_client'

# DocumentAI接続テストツール
class ConnectionTester
  def self.run(test_image_path = nil)
    puts "=== DocumentAI 接続テスト ==="
    
    begin
      client = DocumentAIClient.new
      
      if client.demo_mode
        puts "❌ デモモードです。本番APIの接続テストはできません。"
        return false
      end
      
      puts "✅ DocumentAI クライアント初期化成功"
      
      # テスト画像での簡単なOCR実行
      if test_image_path && File.exist?(test_image_path)
        puts "\n--- テスト画像でOCR実行 ---"
        puts "ファイル: #{test_image_path}"
        
        result = client.extract_text(test_image_path)
          if result['error']
          puts "❌ OCRエラー: #{result['error']}"
          return false
        else
          puts "✅ OCR成功"
          puts "抽出テキスト: #{result['ocr_text'][0..100]}#{'...' if result['ocr_text'].length > 100}"
          puts "信頼度: #{result['confidence']}"
          puts "場所: #{result['location_value'] || '未検出'}"
          puts "日付: #{result['date_value'] || '未検出'}"
          puts "台数: #{result['count_value'] || '未検出'}"
          return true
        end
      else
        puts "✅ 基本接続テスト成功"
        puts "実際のOCRテストを行うには画像ファイルを指定してください"
        return true
      end
      
    rescue => e
      puts "❌ 接続テスト失敗: #{e.message}"
      puts e.backtrace.first(3) if ENV['DEBUG']
      return false
    end
  end
end

if __FILE__ == $0
  test_image_path = ARGV[0]
  
  puts "使用方法: ruby bin/test_connection.rb [test_image.jpg]"
  puts ""
  
  success = ConnectionTester.run(test_image_path)
  
  if success
    puts "\n🎉 DocumentAI接続テスト成功！"
    exit 0
  else
    puts "\n❌ DocumentAI接続テスト失敗"
    puts "\n解決方法:"
    puts "1. config/document_ai.json の設定を確認"
    puts "2. Google Cloud認証を確認: gcloud auth application-default login"
    puts "3. DocumentAI APIが有効化されているか確認"
    exit 1
  end
end
