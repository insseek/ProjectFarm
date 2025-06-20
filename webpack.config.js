const webpack = require("webpack");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CleanWebpackPlugin = require("clean-webpack-plugin");
// const UglifyJsPlugin = require('uglifyjs-webpack-plugin');
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin')// 最大化压缩css
const path = require("path");
const glob = require("glob");


//开发与生产环境的变量
let NODE_ENV = process.env.NODE_ENV;
let dev_serve = {};
if (NODE_ENV == 'development') {
    dev_serve = {
        contentBase: path.resolve(__dirname, "dist"),
        host: "localhost",
        port: "8099",
        open: false, // 开启浏览器
        compress: false,
        // hot: true
    }
}

let globPath = './**/entry/*.js';
let filePath = glob.sync(globPath)
//入口配置
let entries = {};
//出口目录
let outputsPath = '';
for (let i = 0; i < filePath.length; i++) {
    outputsPath = './static/farm_output';
    let fpath = filePath[i];
    let fileName = fpath.split('/')[fpath.split('/').length - 1];
    let entryName = fileName.split('.')[0];
    entries[entryName] = fpath;
}

let config = {
    mode: NODE_ENV,
    devtool: NODE_ENV == 'production' ? 'source-map' : 'inline-source-map',
    entry: entries,
    output: {
        // path: path.resolve(__dirname, './projects/static/projects/scripts/output'),
        path: path.resolve(__dirname, outputsPath),
        filename: '[name].js',
        chunkFilename: "[name]-[hash:5].chunk.js"
    },

    //开发时使用
    devServer: dev_serve,

    module: {
        rules: [
            {
                test: /\.js$||\.jsx?/,
                exclude: /node_modules/,
                loader: 'babel-loader',
                options: {
                    presets: ['es2015', 'react'],
                    plugins: [
                        ["import", {
                            "libraryName": "antd",
                            "libraryDirectory": "es",
                            "style": "css" // `style: true` 会加载 less 文件
                            // "style": "true" // `style: true` 会加载 less 文件 更改antd主题色时使用
                        }]
                    ]
                },
            },
            {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    // MiniCssExtractPlugin.loader, //单独处理css 不可以在dev中使用
                    'style-loader',
                    'css-loader',
                    'sass-loader',
                ],
            },
            {
                //配置antd主题色 页面中需要 // import 'antd/dist/antd.less';
                test: /\.less$/,
                use: [
                    {loader: 'style-loader'},
                    {loader: 'css-loader'},
                    {
                        loader: 'less-loader',
                        options: {
                            modifyVars: {
                                'primary-color': '#2161fd',
                                'border-color-base': '#e4e6ea',
                                'border-radius-base': '2px',
                                'box-shadow-base': '0 2px 16px 0 rgba(33, 43, 54, 0.08), 0 1px 3px 0 rgba(64, 66, 69, 0.12), 0 0 0 1px rgba(78, 84, 96, 0.1);',
                            },
                            javascriptEnabled: true,
                        }
                    },
                ],
            },
            {
                test: /\.(png|jpg|gif|jpeg|svg)$/,
                use: [
                    {
                        loader: "url-loader",
                        options: {
                            // name: "[name].[hash:5].[ext]",
                            // limit: 1024, // size <= 1kib
                            // outputPath: "img"
                        }
                    }
                ]
            }
        ],
    },
    optimization: {
        splitChunks: {
            automaticNameDelimiter: '-',
            name: 'common',
            cacheGroups: {
                vendor: {
                    test: /node_modules/,
                    chunks: "initial",
                    filename: '[name].bundle.js',
                    priority: 10,
                    enforce: true
                }
            }
        },
        minimize: false
    },
    plugins: [],
    resolve: {
        alias: {
            '@components': path.resolve(__dirname, './farmbase/static/components'),
        }
    }
}


if (NODE_ENV == 'production') {
    config.plugins = config.plugins.concat(
        new CleanWebpackPlugin(outputsPath),
        // new UglifyJsPlugin({uglifyOptions: {
        //         output: {
        //             comments: false,
        //         },
        //         compress: {
        //             drop_console: true,
        //             pure_funcs: ['console.log'] // 移除console
        //         }
        //     },
        // }),
        new webpack.DefinePlugin({                                        // 把引入的React切换到产品版本
            'process.env.NODE_ENV': '"production"'
        }),
    )

}
module.exports = config;

