# This file is auto-generated from the current state of the database.
# Instead of editing this file, please use the migrations feature of
# Active Record to incrementally modify your database.

ActiveRecord::Schema[7.1].define(version: 2026_09_19_004201) do
  enable_extension "plpgsql"

  create_table "users", force: :cascade do |t|
    t.string "username", null: false
    t.string "email", null: false
    t.string "password_digest", null: false
    t.boolean "is_admin", default: false
    t.boolean "is_active", default: true
    t.datetime "last_login_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["email"], unique: true
    t.index ["username"], unique: true
  end

  create_table "api_keys", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.string "name", null: false
    t.string "key_hash", null: false
    t.text "permissions"
    t.datetime "expires_at"
    t.datetime "last_used_at"
    t.datetime "created_at", null: false
    t.index ["user_id"]
    t.index ["key_hash"], unique: true
  end

  create_table "nodes", force: :cascade do |t|
    t.string "name", null: false
    t.string "hostname", null: false
    t.string "internal_address", null: false
    t.integer "management_port", default: 8443
    t.string "authentication_key_hash"
    t.boolean "enabled", default: true
    t.datetime "last_heartbeat_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["name"], unique: true
  end

  create_table "servers", force: :cascade do |t|
    t.bigint "node_id"
    t.bigint "owner_id"
    t.string "name", null: false
    t.string "display_name", null: false
    t.string "status", default: "unknown"
    t.integer "player_count", default: 0
    t.integer "max_player_count"
    t.integer "ram_min_mb", default: 2048
    t.integer "ram_max_mb", default: 4096
    t.integer "ram_usage_mb"
    t.float "cpu_usage_percent"
    t.string "internal_address"
    t.integer "port"
    t.text "start_command"
    t.text "stop_command"
    t.string "working_directory"
    t.datetime "status_updated_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["name"], unique: true
    t.index ["node_id"]
    t.index ["owner_id"]
  end

  create_table "server_permissions", force: :cascade do |t|
    t.bigint "server_id", null: false
    t.bigint "user_id", null: false
    t.integer "permissions", default: 0
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["server_id", "user_id"], unique: true
  end

  create_table "audit_logs", force: :cascade do |t|
    t.bigint "user_id"
    t.string "action", null: false
    t.string "resource_type"
    t.bigint "resource_id"
    t.string "ip_address"
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.index ["user_id"]
    t.index ["created_at"]
  end

  add_foreign_key "api_keys", "users"
  add_foreign_key "servers", "nodes"
  add_foreign_key "servers", "users", column: "owner_id"
  add_foreign_key "server_permissions", "servers"
  add_foreign_key "server_permissions", "users"
  add_foreign_key "audit_logs", "users"
end