const webpack = require("webpack");
const CleanWebpackPlugin = require("clean-webpack-plugin");

const merge = require('webpack-merge');
const common = require('./webpack.common.js');
// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

let outputsPath = './static/farm_output';
let config = {
    mode: 'production',
    devtool: false,

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
                    test: /[\\/]node_modules[\\/]/,
                    name: 'commons',
                    priority: 80,
                    enforce: true,
                },

            }
        },
        minimize: true
    },

    plugins: [
        new CleanWebpackPlugin(outputsPath),
        // 把引入的React切换到产品版本
        new webpack.DefinePlugin({
            'process.env.NODE_ENV': '"production"'
        }),
        /*new BundleAnalyzerPlugin({
            analyzerMode: 'server',
            analyzerHost: '127.0.0.1',
            analyzerPort: 8889,
        })*/
    ],

}

module.exports = merge(common,config);

