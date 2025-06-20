const path = require("path");
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

let config = {
    mode: 'development',
    // devtool: 'inline-source-map',
    devtool: 'cheap-source-map',

    //开发时使用
    devServer: {
        contentBase: path.resolve(__dirname, "dist"),
        host: "localhost",
        port: "8099",
        open: false, // 开启浏览器
        compress: true,
    },

    optimization: {
        splitChunks: {
            name: true,
            cacheGroups: {
                antd: {
                    chunks: 'initial',
                    test: /(antd|ant-design)/,
                    name: 'antd',
                    priority: 100,
                },
                moment: {
                    chunks: 'initial',
                    test: /moment/,
                    name: 'moment',
                    priority: 100,
                },
                commons: {
                    chunks: 'all',
                    // test: /[\\/]node_modules[\\/]/,
                    // minChunks: 2,
                    name: 'commons',
                    priority: 80,
                },

            }
        },
        minimize: false
    },

    plugins: [
    ]
}
module.exports = merge(common,config);

