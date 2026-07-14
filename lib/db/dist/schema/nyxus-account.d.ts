export declare const nyxusAccountBlobs: import("drizzle-orm/pg-core").PgTableWithColumns<{
    name: "nyxus_account_blobs";
    schema: undefined;
    columns: {
        token: import("drizzle-orm/pg-core").PgColumn<{
            name: "token";
            tableName: "nyxus_account_blobs";
            dataType: "string";
            columnType: "PgText";
            data: string;
            driverParam: string;
            notNull: true;
            hasDefault: false;
            isPrimaryKey: true;
            isAutoincrement: false;
            hasRuntimeDefault: false;
            enumValues: [string, ...string[]];
            baseColumn: never;
            identity: undefined;
            generated: undefined;
        }, {}, {}>;
        blob: import("drizzle-orm/pg-core").PgColumn<{
            name: "blob";
            tableName: "nyxus_account_blobs";
            dataType: "custom";
            columnType: "PgCustomColumn";
            data: Buffer<ArrayBufferLike>;
            driverParam: unknown;
            notNull: true;
            hasDefault: false;
            isPrimaryKey: false;
            isAutoincrement: false;
            hasRuntimeDefault: false;
            enumValues: undefined;
            baseColumn: never;
            identity: undefined;
            generated: undefined;
        }, {}, {
            pgColumnBuilderBrand: "PgCustomColumnBuilderBrand";
        }>;
        size: import("drizzle-orm/pg-core").PgColumn<{
            name: "size";
            tableName: "nyxus_account_blobs";
            dataType: "number";
            columnType: "PgInteger";
            data: number;
            driverParam: string | number;
            notNull: true;
            hasDefault: false;
            isPrimaryKey: false;
            isAutoincrement: false;
            hasRuntimeDefault: false;
            enumValues: undefined;
            baseColumn: never;
            identity: undefined;
            generated: undefined;
        }, {}, {}>;
        contentType: import("drizzle-orm/pg-core").PgColumn<{
            name: "content_type";
            tableName: "nyxus_account_blobs";
            dataType: "string";
            columnType: "PgText";
            data: string;
            driverParam: string;
            notNull: true;
            hasDefault: true;
            isPrimaryKey: false;
            isAutoincrement: false;
            hasRuntimeDefault: false;
            enumValues: [string, ...string[]];
            baseColumn: never;
            identity: undefined;
            generated: undefined;
        }, {}, {}>;
        updatedAt: import("drizzle-orm/pg-core").PgColumn<{
            name: "updated_at";
            tableName: "nyxus_account_blobs";
            dataType: "date";
            columnType: "PgTimestamp";
            data: Date;
            driverParam: string;
            notNull: true;
            hasDefault: true;
            isPrimaryKey: false;
            isAutoincrement: false;
            hasRuntimeDefault: false;
            enumValues: undefined;
            baseColumn: never;
            identity: undefined;
            generated: undefined;
        }, {}, {}>;
    };
    dialect: "pg";
}>;
export type NyxusAccountBlob = typeof nyxusAccountBlobs.$inferSelect;
//# sourceMappingURL=nyxus-account.d.ts.map