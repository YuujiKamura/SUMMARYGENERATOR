#!/usr/bin/env ruby
# -*- coding: utf-8 -*-

require_relative '../lib/document_ai_client'

# DocumentAI設定確認ツール
class ConfigChecker
  def self.run(config_path = nil)
    puts "=== DocumentAI 設定確認ツール ==="
    
    client = DocumentAIClient.new(config_path)
    
    if client.demo_mode
      puts "\n❌ デモモードで動作中"
      puts "本番DocumentAI APIを使用するには以下を確認してください:"
      puts ""
      puts "1. config/document_ai.json に正しい設定があるか"
      puts "2. Google Cloud SDKがインストールされているか"
      puts "3. 認証情報が設定されているか"
      puts ""
      puts "現在の設定:"
      puts client.instance_variable_get(:@config).inspect
    else
      puts "\n✅ 本番モードで動作中"
      puts "DocumentAI APIが利用可能です"
    end
  end
end

# 環境変数設定例を表示
def show_env_example
  puts "\n=== 環境変数設定例 ==="
  puts "export GOOGLE_CLOUD_PROJECT_ID='your-actual-project-id'"
  puts "export DOCUMENT_AI_LOCATION='us'"
  puts "export DOCUMENT_AI_PROCESSOR_ID='your-actual-processor-id'"
  puts "export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account-key.json'"
end

if __FILE__ == $0
  begin
    config_path = ARGV[0]
    ConfigChecker.run(config_path)
    show_env_example
  rescue => e
    puts "エラー: #{e.message}"
    puts e.backtrace if ENV['DEBUG']
    exit 1
  end
end
